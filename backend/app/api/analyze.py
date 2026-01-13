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
from PIL import ImageOps
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


def process_image(file_bytes: bytes, max_size: int = 8192) -> bytes:
    """
    处理上传的图片：
    1. 验证格式
    2. 保留原图分辨率（仅在超大图片时压缩）
    3. 转换为 JPEG

    注意：max_size 提升到 8192px，确保坐标精度
    Gemini 2.5 支持最大 7MB，Gemini 3 支持最大 20MB
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        original_size = img.size

        # 统一方向（避免 EXIF Orientation 导致“同图不同坐标”）
        img = ImageOps.exif_transpose(img)
        
        # 转换为 RGB（去除透明通道）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # 按比例缩放（提高阈值以保持更高分辨率）
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"图片已压缩: {original_size} -> {img.size}")
        else:
            logger.info(f"图片无需压缩: {original_size}")
        
        # 转为 JPEG bytes（提高质量到 95）
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片格式无效或已损坏"
        )


def _normalize_mime_type(content_type: Optional[str]) -> Optional[str]:
    if not content_type:
        return None
    ct = content_type.strip().lower()
    if ct == "image/jpg":
        return "image/jpeg"
    if ct.startswith("image/"):
        return ct
    return None


def _pil_format_to_mime(pil_format: Optional[str]) -> Optional[str]:
    if not pil_format:
        return None
    fmt = pil_format.upper()
    if fmt == "JPEG":
        return "image/jpeg"
    if fmt == "PNG":
        return "image/png"
    if fmt == "WEBP":
        return "image/webp"
    if fmt == "GIF":
        return "image/gif"
    if fmt == "BMP":
        return "image/bmp"
    if fmt == "TIFF":
        return "image/tiff"
    return None


def prepare_image_for_gemini(
    file_bytes: bytes,
    content_type: Optional[str],
    *,
    max_dim: int = 8192,
    max_bytes: int = 20 * 1024 * 1024,
) -> tuple[bytes, str]:
    """
    为 Gemini 准备图片输入：优先保持原始文件字节，以最大化与 AI Studio 对齐。

    常见偏移根因：
    - 后端把上传图片重新编码成 JPEG，丢失 EXIF 方向等元数据；
    - 前端展示的是原文件（浏览器会自动应用 EXIF 方向），导致“模型看到的图”和“用户看到的图”不一致；
    - 或 mime_type 声明不匹配，导致服务端解码行为异常。

    返回：(bytes, mime_type)
    """
    normalized_ct = _normalize_mime_type(content_type)

    try:
        img = Image.open(io.BytesIO(file_bytes))
        pil_mime = _pil_format_to_mime(img.format)
        mime_type = normalized_ct or pil_mime or "image/jpeg"

        exif = getattr(img, "getexif", lambda: None)()
        orientation = 1
        if exif:
            orientation = int(exif.get(274, 1) or 1)

        within_dim = max(img.size) <= max_dim
        within_bytes = len(file_bytes) <= max_bytes

        orientation_ok = (orientation == 1)
        keep_mimes = {"image/jpeg", "image/png", "image/webp"}

        # 满足条件就不做任何处理：保持字节不变（最贴近 AI Studio 行为）
        # - JPEG 额外要求 EXIF Orientation 为 1（否则用户看到的方向可能与模型解码方向不一致）
        if (
            mime_type in keep_mimes
            and within_dim
            and within_bytes
            and (mime_type != "image/jpeg" or orientation_ok)
        ):
            logger.info(
                f"图片保持原始字节发送 Gemini: mime={mime_type}, size={img.size}, bytes={len(file_bytes)}"
            )
            return file_bytes, mime_type

        # 否则：做最小必要的标准化（方向/透明通道/超大尺寸/输出格式）
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        out_bytes = buffer.getvalue()
        logger.info(
            "图片已标准化后发送 Gemini: "
            f"in_mime={mime_type}, in_size={img.size}, in_bytes={len(file_bytes)}, "
            f"out_mime=image/jpeg, out_bytes={len(out_bytes)}"
        )
        return out_bytes, "image/jpeg"
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
    child_bytes_raw = await child.read()
    child_bytes, child_mime_type = prepare_image_for_gemini(child_bytes_raw, child.content_type)

    father_bytes = None
    father_mime_type = None
    if father:
        father_bytes_raw = await father.read()
        father_bytes, father_mime_type = prepare_image_for_gemini(father_bytes_raw, father.content_type)

    mother_bytes = None
    mother_mime_type = None
    if mother:
        mother_bytes_raw = await mother.read()
        mother_bytes, mother_mime_type = prepare_image_for_gemini(mother_bytes_raw, mother.content_type)
    
    try:
        # 调用 Gemini 分析
        result = await gemini_service.analyze_family_photos(
            child_image=child_bytes,
            child_mime_type=child_mime_type,
            father_image=father_bytes,
            father_mime_type=father_mime_type,
            mother_image=mother_bytes,
            mother_mime_type=mother_mime_type,
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
