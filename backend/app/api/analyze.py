"""
照片分析 API
对应设计文档 7.2 上传与分析
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import os
import uuid
from app.core.database import get_db
from app.core.config import get_settings
from app.models import CardKey, CardStatus
from app.services.gemini_service import gemini_service
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/analyze", tags=["照片分析"])


class FaceCenter(BaseModel):
    """脸部中心点（鼻尖位置）"""
    x: int
    y: int


class AnalysisResultItem(BaseModel):
    """单个分析结果项"""
    part: str
    similar_to: str
    similarity_score: int
    description: str


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    analysis_results: List[AnalysisResultItem]
    face_center: Optional[FaceCenter] = None
    face_width: Optional[int] = None


async def verify_authorization(
    authorization: str = Header(..., description="Bearer <兑换码>"),
    db: AsyncSession = Depends(get_db)
) -> CardKey:
    """
    验证授权头中的兑换码
    格式: Authorization: Bearer <code>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的授权格式"
        )
    
    code = authorization[7:].strip().upper()
    
    stmt = select(CardKey).where(CardKey.code == code)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    
    is_test_key = (code == "TEST8888")

    if not card or (card.status != CardStatus.USED and not is_test_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="兑换码未激活或无效"
        )
    
    # 如果是测试码且未激活，自动激活（方便直接调用 analyze 接口）
    if is_test_key and card.status != CardStatus.USED:
        card.status = CardStatus.USED
        card.activated_at = datetime.now()
        # 测试模式下不需要严格校验 device_id，设置一个占位符即可
        if not card.device_id:
            card.device_id = "TEST_DEV_MODE"
        await db.commit()
    
    return card


def process_image(file_bytes: bytes, max_size: int = 1024) -> bytes:
    """
    处理上传的图片：
    1. 验证格式
    2. 压缩到合理尺寸（节省 API 调用成本）
    3. 转换为 JPEG
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        
        # 转换为 RGB（去除透明通道）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # 按比例缩放
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 转为 JPEG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片格式无效或已损坏"
        )


@router.post("", response_model=AnalysisResponse)
async def analyze_photos(
    child: UploadFile = File(..., description="孩子照片（必填）"),
    father: Optional[UploadFile] = File(None, description="父亲照片（选填）"),
    mother: Optional[UploadFile] = File(None, description="母亲照片（选填）"),
    card: CardKey = Depends(verify_authorization),
    db: AsyncSession = Depends(get_db)
):
    """
    上传照片并进行 AI 分析
    
    逻辑（来自设计文档）：
    1. 校验 code 是否在 card_keys 表中且已激活
    2. 调用 Gemini API 分析
    3. 将 JSON 存入 card_keys.result_cache
    4. 返回 JSON 给前端
    """
    # 检查是否至少有一个家长照片
    if not father and not mother:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少上传父亲或母亲的照片"
        )
    
    # 读取并处理图片
    child_bytes = process_image(await child.read())
    father_bytes = process_image(await father.read()) if father else None
    mother_bytes = process_image(await mother.read()) if mother else None
    
    try:
        # 调用 Gemini 分析
        result = await gemini_service.analyze_family_photos(
            child_image=child_bytes,
            father_image=father_bytes,
            mother_image=mother_bytes
        )
        
        # 缓存结果到数据库
        card.result_cache = json.dumps(result, ensure_ascii=False)
        await db.commit()
        
        logger.info(f"分析完成，兑换码: {card.code}")
        
        return AnalysisResponse(
            success=True,
            analysis_results=result.get("analysis_results", []),
            face_center=result.get("face_center"),
            face_width=result.get("face_width")
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("AI 分析异常")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 分析服务暂时不可用，请稍后重试"
        )


@router.get("/result")
async def get_cached_result(
    card: CardKey = Depends(verify_authorization)
):
    """
    获取缓存的分析结果
    用于页面刷新后恢复结果
    """
    if not card.result_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到分析结果，请重新上传分析"
        )
    
    result = json.loads(card.result_cache)
    return {
        "success": True,
        "analysis_results": result.get("analysis_results", []),
        "face_center": result.get("face_center"),
        "face_width": result.get("face_width")
    }
