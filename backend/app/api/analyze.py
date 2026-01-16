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
    
    
    if not card or card.status != CardStatus.USED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="兑换码未激活或无效"
        )
    
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


def format_mb(size_in_bytes: int) -> str:
    return f"{size_in_bytes / (1024 * 1024):.2f} MB"

def prepare_image_for_gemini(
    file_bytes: bytes,
    content_type: Optional[str],
    label: str,
    *,
    max_dim: int = 8192,
    max_bytes: int = 10 * 1024 * 1024,
    quality: int = 95
) -> tuple[bytes, str]:
    """
    为 Gemini 准备图片输入
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

        # 满足条件: 保持原样
        if (
            mime_type in keep_mimes
            and within_dim
            and within_bytes
            and (mime_type != "image/jpeg" or orientation_ok)
        ):
            logger.info(
                f"[{label}] 保持原始发送: mime={mime_type}, "
                f"尺寸={img.size}, 大小={len(file_bytes)} bytes ({format_mb(len(file_bytes))})"
            )
            return file_bytes, mime_type

        # 否则: 标准化处理
        # 1. 自动旋转
        img = ImageOps.exif_transpose(img)
        # 2. 转 RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # 3. 压缩尺寸 (仅当超过 max_dim 时)
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"[{label}] 触发尺寸压缩: {max_dim}px 限制")
        
        # 4. 重新编码 (JPEG)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        out_bytes = buffer.getvalue()
        
        logger.info(
            f"[{label}] 标准化处理后 (Q={quality}): "
            f"in_mime={mime_type}, in_size={img.size}, in_bytes={format_mb(len(file_bytes))} -> "
            f"out_mime=image/jpeg, out_bytes={format_mb(len(out_bytes))}"
        )
        return out_bytes, "image/jpeg"
    except Exception as e:
        logger.error(f"[{label}] 图片处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} 图片格式无效或已损坏"
        )



# 简单的内存锁，防止同一激活码并发调用 Gemini
# 注意：多实例部署时依然可能并发，但 Docker Compose 单实例足够用
processing_codes = set()

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
    """
    # 0. 并发控制: 内存锁
    if card.code in processing_codes:
        logger.warning(f"拒绝并发请求: {card.code} 正在分析中")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="分析正在进行中，请耐心等待..."
        )

    # 检查是否至少有一个家长照片
    if not father and not mother:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少上传父亲或母亲的照片"
        )
    
    # 【安全加固 2026-01-15】: 防止二次分析覆盖结果
    if card.result_cache:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此兑换码已使用且结果已生成，禁止重复分析"
        )
    
    
    try:
        # 上锁
        processing_codes.add(card.code)

        # 读取并处理图片
        # 1. 孩子照片: 阈值 6MB。保持高分辨率 (max_dim=8192)，压缩质量 95 (轻微)。
        # 关键：避免 resize 导致坐标偏移。
        child_bytes_raw = await child.read()
        child_bytes, child_mime_type = prepare_image_for_gemini(
            child_bytes_raw, 
            child.content_type, 
            "Child",
            max_dim=8192, 
            max_bytes=6 * 1024 * 1024,
            quality=90
        )

        # 2. 父亲照片: 阈值 3MB。可以压缩 (max_dim=2048)，质量 85。
        father_bytes = None
        father_mime_type = None
        if father:
            father_bytes_raw = await father.read()
            father_bytes, father_mime_type = prepare_image_for_gemini(
                father_bytes_raw, 
                father.content_type, 
                "Father",
                max_dim=2048,
                max_bytes=3 * 1024 * 1024,
                quality=85
            )

        # 3. 母亲照片: 阈值 3MB。可以压缩 (max_dim=2048)，质量 85。
        mother_bytes = None
        mother_mime_type = None
        if mother:
            mother_bytes_raw = await mother.read()
            mother_bytes, mother_mime_type = prepare_image_for_gemini(
                mother_bytes_raw, 
                mother.content_type, 
                "Mother",
                max_dim=2048,
                max_bytes=3 * 1024 * 1024,
                quality=85
            )


        # 调用 Gemini 分析
        result = await gemini_service.analyze_family_photos(
            child_image=child_bytes,
            child_mime_type=child_mime_type,
            father_image=father_bytes,
            father_mime_type=father_mime_type,
            mother_image=mother_bytes,
            mother_mime_type=mother_mime_type,
        )
        
        # 保存图片到磁盘，生成持久化 URL (用于页面刷新/意外退出恢复)
        images_dir = "data/images"
        # os.makedirs(images_dir, exist_ok=True) # main.py 里已经创建了，这里可以直接用
        
        saved_paths = {}
        
        # 保存 Child
        child_filename = f"{card.code}_child.jpg"
        child_path = os.path.join(images_dir, child_filename)
        with open(child_path, "wb") as f:
            f.write(child_bytes)
        saved_paths["child"] = f"/api/images/{child_filename}" # 前端可访问的 URL
        
        # 保存 Father
        if father_bytes:
            father_filename = f"{card.code}_father.jpg"
            father_path = os.path.join(images_dir, father_filename)
            with open(father_path, "wb") as f:
                f.write(father_bytes)
            saved_paths["father"] = f"/api/images/{father_filename}"
            
        # 保存 Mother
        if mother_bytes:
            mother_filename = f"{card.code}_mother.jpg"
            mother_path = os.path.join(images_dir, mother_filename)
            with open(mother_path, "wb") as f:
                f.write(mother_bytes)
            saved_paths["mother"] = f"/api/images/{mother_filename}"
        
        # 缓存结果到数据库
        card.result_cache = json.dumps(result, ensure_ascii=False)
        card.image_paths = json.dumps(saved_paths, ensure_ascii=False) # 保存图片路径
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("AI 分析异常")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 分析服务暂时不可用，请稍后重试"
        )
    finally:
        # 释放锁
        processing_codes.discard(card.code)


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
    
    # 尝试解析保存的图片路径
    images = None
    if card.image_paths:
        try:
            images = json.loads(card.image_paths)
        except Exception:
            logger.warning(f"Failed to parse image_paths for card {card.code}")
            
    return {
        "success": True,
        "analysis_results": result.get("analysis_results", []),
        "face_center": result.get("face_center"),
        "face_width": result.get("face_width"),
        "images": images  # 返回图片 URL
    }
