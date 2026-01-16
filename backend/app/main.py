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
from app.core.security import get_current_admin
from fastapi import Depends
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
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
    lifespan=lifespan,
    # 禁用默认文档路由（由下方自定义路由接管，并增加密码保护）
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 (API)
# 注册路由 (API)
app.include_router(api_router)

# 挂载静态文件目录 (用于存储和访问图片)
from fastapi.staticfiles import StaticFiles
import os

os.makedirs("data/images", exist_ok=True)
app.mount("/api/images", StaticFiles(directory="data/images"), name="images")


# --- 路由：文档安全保护 ---
# 只有通过 Basic Auth 的管理员才能看到文档
# 注意：生产环境 enable_docs 仍然控制是否彻底关闭，如果开启则强制要求密码

@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(username: str = Depends(get_current_admin)):
    """受保护的 Swagger UI"""
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API 文档 - 亲子基因探测器")

@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(username: str = Depends(get_current_admin)):
    """受保护的 ReDoc"""
    return get_redoc_html(openapi_url="/openapi.json", title="API 文档 - 亲子基因探测器")

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(username: str = Depends(get_current_admin)):
    """受保护的 OpenAPI Schema"""
    return app.openapi()


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
