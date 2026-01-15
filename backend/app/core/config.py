"""
应用配置模块
使用 pydantic-settings 从环境变量加载配置
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os


class Settings(BaseSettings):
    """应用配置类"""
    
    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"  # 默认模型
    gemini_temperature: float = 1.0
    gemini_enable_thinking: bool = True
    
    # 数据库
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    
    # 服务器
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    enable_docs: bool = False  # 生产环境默认关闭 API 文档
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    # 数据保留
    data_retention_hours: int = 24
    
    # 临时存储
    temp_storage_path: str = "./data/temp"
    
    # 测试配置
    test_card_code: str = "TEST8888"

    # 管理员配置 (HTTP Basic Auth)
    admin_username: str = "admin"
    admin_password: str = "admin888"  # 生产环境请修改！
    
    @property
    def cors_origins_list(self) -> List[str]:
        """将逗号分隔的 CORS 源转换为列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    return Settings()
