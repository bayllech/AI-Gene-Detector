"""
兑换码相关 API
对应设计文档 7.1 验证兑换码
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.models import CardKey, CardStatus
import logging

logger = logging.getLogger(__name__)
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


@router.post("/verify", response_model=VerifyCodeResponse)
async def verify_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db)
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
            restored=False
        )
    
    else:
        # 特殊处理测试码：允许任意设备即使在已使用状态下也能通过（方便测试）
        # 或者你也可以选择让它重置绑定。这里我们选择：如果匹配则由于，不匹配则警告还是允许？
        # 用户需求是 "设置为测试专用"，通常意味着不限制设备。
        is_test_key = (code == "TEST8888")

        # 已使用，检查设备匹配
        if card.device_id == device_id or is_test_key:
            if is_test_key and card.device_id != device_id:
               # 如果是测试码且设备变了，静默更新设备ID以便后续流程正常
               card.device_id = device_id
               await db.commit()
               logger.info(f"测试码 {code} 重新绑定到设备 {device_id[:8]}...")

            logger.info(f"兑换码 {code} 恢复会话，设备 {device_id[:8]}...")
            return VerifyCodeResponse(
                success=True,
                message="会话已恢复",
                restored=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此码已被其他设备激活"
            )


class CreateCodeRequest(BaseModel):
    """创建兑换码请求（管理接口）"""
    codes: list[str]


class CreateCodeResponse(BaseModel):
    """创建兑换码响应"""
    created: int
    skipped: int


@router.post("/batch-create", response_model=CreateCodeResponse)
async def batch_create_codes(
    request: CreateCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    批量创建兑换码（管理接口）
    用于导入从阿奇索等平台生成的兑换码
    """
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
