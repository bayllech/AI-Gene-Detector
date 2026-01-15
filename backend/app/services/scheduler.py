"""
定时任务模块
负责清理过期数据（设计文档 第9节）
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.core.database import async_session
from app.core.config import get_settings
from app.models import CardKey
import logging
import os

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def cleanup_expired_data():
    """
    清理过期数据
    
    来自设计文档：
    - 每小时运行一次
    - 删除激活时间超过 24 小时的记录
    - 同时删除对应的临时文件
    """
    async with async_session() as db:
        try:
            # 计算过期时间点
            expiry_time = datetime.now() - timedelta(hours=settings.data_retention_hours)
            
            # 查询要删除的记录（用于清理文件）
            from sqlalchemy import select
            stmt = select(CardKey).where(
                CardKey.activated_at < expiry_time,
                CardKey.activated_at.isnot(None),
                CardKey.code != settings.test_card_code
            )
            result = await db.execute(stmt)
            expired_cards = result.scalars().all()
            
            # 删除临时文件
            for card in expired_cards:
                if card.image_paths:
                    import json
                    try:
                        paths = json.loads(card.image_paths)
                        for path in paths:
                            if os.path.exists(path):
                                os.remove(path)
                                logger.debug(f"已删除临时文件: {path}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {e}")
            
            # 删除数据库记录
            delete_stmt = delete(CardKey).where(
                CardKey.activated_at < expiry_time,
                CardKey.activated_at.isnot(None),
                CardKey.code != settings.test_card_code
            )
            result = await db.execute(delete_stmt)
            await db.commit()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"清理过期数据完成，删除 {deleted_count} 条记录")
            
        except Exception as e:
            logger.exception("清理过期数据时发生错误")


def start_scheduler():
    """启动定时任务调度器"""
    # 每小时执行一次清理任务
    scheduler.add_job(
        cleanup_expired_data,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_expired_data",
        name="清理过期数据",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("定时任务调度器已启动")


def stop_scheduler():
    """停止定时任务调度器"""
    scheduler.shutdown()
    logger.info("定时任务调度器已停止")
