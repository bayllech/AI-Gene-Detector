"""
兑换码数据模型
对应设计文档中的 card_keys 表
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class CardStatus(enum.IntEnum):
    """兑换码状态枚举"""
    UNUSED = 0      # 未使用
    USED = 1        # 已使用


class CardKey(Base):
    """兑换码表"""
    __tablename__ = "card_keys"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 兑换码，唯一索引
    code = Column(String(20), unique=True, index=True, nullable=False)
    
    # 状态: 0=未使用, 1=已使用
    status = Column(Integer, default=CardStatus.UNUSED, nullable=False)
    
    # 绑定的设备指纹
    device_id = Column(String(64), nullable=True, index=True)
    
    # 激活时间
    activated_at = Column(DateTime, nullable=True)
    
    # 缓存 Gemini 返回的 JSON 结果
    result_cache = Column(Text, nullable=True)
    
    # 临时图片路径 (JSON 格式)
    image_paths = Column(Text, nullable=True)
    
    # 创建时间
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<CardKey(code={self.code}, status={self.status})>"
