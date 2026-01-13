"""
AI 亲子基因探测器 - 后端服务入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.core.database import init_db
from app.api import api_router
from app.services.scheduler import start_scheduler, stop_scheduler
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 正在启动 AI 亲子基因探测器后端服务...")
    
    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")
    
    # 启动定时任务
    start_scheduler()
    logger.info("✅ 定时任务已启动")
    
    yield
    
    # 关闭时
    stop_scheduler()
    logger.info("👋 服务已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI 亲子基因探测器",
    description="基于 Google Gemini 的家庭面部特征分析服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "AI 亲子基因探测器",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}
