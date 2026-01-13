"""
数据库连接模块
使用 SQLAlchemy 异步引擎
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings
import os

settings = get_settings()

# 确保数据目录存在
os.makedirs(os.path.dirname(settings.database_url.replace("sqlite+aiosqlite:///", "")) or "./data", exist_ok=True)

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # 调试模式下打印 SQL
    future=True
)

# 创建异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


async def get_db() -> AsyncSession:
    """依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
