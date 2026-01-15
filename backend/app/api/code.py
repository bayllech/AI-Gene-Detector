"""
兑换码相关 API
对应设计文档 7.1 验证兑换码
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import verify_rate_limiter, get_current_admin
from app.models import CardKey, CardStatus
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/code", tags=["兑换码"])


class VerifyCodeRequest(BaseModel):
    """验证兑换码请求体"""
    code: str
    device_id: str


class VerifyCodeResponse(BaseModel):
    """验证兑换码响应体"""
    success: bool
    message: str
    restored: bool = False  # 是否为恢复会话
    success: bool
    message: str
    restored: bool = False  # 是否为恢复会话
    has_result: bool = False  # 标记是否已有分析结果


class CheckStatusResponse(BaseModel):
    """状态检查响应"""
    valid: bool
    has_result: bool
    is_expired: bool = False
    message: str = ""


@router.post("/verify", response_model=VerifyCodeResponse)
async def verify_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_rate_limiter)
):
    """
    验证兑换码
    
    逻辑（来自设计文档）：
    1. 查库：码是否存在？
    2. 若 status=0 (未使用)：更新 status=1, device_id=current, activated_at=now。返回 Success。
    3. 若 status=1 (已使用)：检查 device_id 是否匹配。
       - 匹配 -> 返回 Success (恢复会话)。
       - 不匹配 -> 返回 Error: 此码已被其他设备激活。
    """
    code = request.code.strip().upper()
    device_id = request.device_id.strip()
    
    if not code or not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="兑换码和设备ID不能为空"
        )
    
    # 查询兑换码
    stmt = select(CardKey).where(CardKey.code == code)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="无效的兑换码"
        )
    
    # 检查状态
    if card.status == CardStatus.UNUSED:
        # 首次使用，绑定设备
        card.status = CardStatus.USED
        card.device_id = device_id
        card.activated_at = datetime.now()
        await db.commit()
        
        logger.info(f"兑换码 {code} 首次激活，绑定设备 {device_id[:8]}...")
        return VerifyCodeResponse(
            success=True,
            message="激活成功",
            restored=False,
            has_result=False
        )
    
    else:
        # 【安全熔断】如果已激活超过 24 小时，即视为过期
        if card.activated_at and datetime.now() - card.activated_at > timedelta(hours=settings.data_retention_hours):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此兑换码已过期失效"
            )

        # 已使用，检查安全与状态
        
        # 1. 安全检查：必须是同一台设备（防止盗用）
        if card.device_id != device_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此码已被其他设备激活"
            )

        # 2. 状态检查：是否已经有分析结果？
        if card.result_cache:
            # 已经有结果了 -> 说明服务已完成 -> 禁止二刷，视为失效
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此兑换码已失效（一次性使用）"
            )
        else:
            # 虽然已激活(USED)，但还没出结果 -> 允许用户回来继续上传
            # 这种情况通常是用户在上传页刷新了，或者意外退出了
            logger.info(f"兑换码 {code} 恢复上传会话...")
            return VerifyCodeResponse(
                success=True,
                message="会话已恢复，请继续上传",
                restored=True,
                has_result=False
            )


class CreateCodeRequest(BaseModel):
    """创建兑换码请求（管理接口）"""
    codes: list[str]


class CreateCodeResponse(BaseModel):
    """创建兑换码响应"""
    created: int
    skipped: int


@router.get("/check-status", response_model=CheckStatusResponse)
async def check_status(
    authorization: str = Header(..., description="Bearer <兑换码>"),
    db: AsyncSession = Depends(get_db)
):
    """
    检查兑换码状态（用于前端路由守卫）
    """
    if not authorization.startswith("Bearer "):
         return CheckStatusResponse(valid=False, has_result=False, message="无效的授权格式")
    
    code = authorization[7:].strip().upper()
    
    stmt = select(CardKey).where(CardKey.code == code)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    
    if not card:
        return CheckStatusResponse(valid=False, has_result=False, message="无效的兑换码")
        
    # 过期检查
    if card.activated_at and datetime.now() - card.activated_at > timedelta(hours=settings.data_retention_hours):
         return CheckStatusResponse(valid=False, has_result=False, is_expired=True, message="已过期")

    if card.status != CardStatus.USED:
         return CheckStatusResponse(valid=False, has_result=False, message="未激活")

    return CheckStatusResponse(
        valid=True,
        has_result=bool(card.result_cache),
        is_expired=False
    )


@router.post("/batch-create", response_model=CreateCodeResponse)
async def batch_create_codes(
    request: CreateCodeRequest,
    _: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    批量创建兑换码（管理接口）
    需要 HTTP Basic Auth 管理员验证
    """
    # 鉴权由 Depends(get_current_admin) 自动处理，能进来就是合法的
    created = 0
    skipped = 0
    
    for code in request.codes:
        code = code.strip().upper()
        if not code:
            continue
        
        # 检查是否已存在
        stmt = select(CardKey).where(CardKey.code == code)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        # 创建新兑换码
        new_card = CardKey(code=code)
        db.add(new_card)
        created += 1
    
    await db.commit()
    logger.info(f"批量创建兑换码: 新增 {created}, 跳过 {skipped}")
    
    return CreateCodeResponse(created=created, skipped=skipped)
