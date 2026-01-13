"""
API 路由注册
"""
from fastapi import APIRouter
from app.api.code import router as code_router
from app.api.analyze import router as analyze_router

api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(code_router)
api_router.include_router(analyze_router)
