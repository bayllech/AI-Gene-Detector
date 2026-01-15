"""
安全防护模块
用于处理限流、验证等安全逻辑
"""
from fastapi import Request, HTTPException, status
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# 内存限流存储
# 结构: { "ip_address": [timestamp1, timestamp2, ...] }
# 注意: 在多进程/分布式部署中需要改用 Redis，当前单进程部署使用内存足够
_request_records = defaultdict(list)

# 安全策略配置
LIMIT_WINDOW = 60    # 时间窗口（秒）
MAX_ATTEMPTS = 10    # 窗口内允许的最大失败/尝试次数

async def verify_rate_limiter(request: Request):
    """
    验证接口限流依赖
    防止暴力破解激活码
    """
    # 获取真实 IP (如果有 Nginx 代理，需从 X-Forwarded-For 获取，这里简化取 direct remote)
    client_ip = request.client.host if request.client else "unknown"
    
    now = time.time()
    history = _request_records[client_ip]
    
    # 1. 清理窗口期的旧记录
    # 移除所有早于 (now - LIMIT_WINDOW) 的记录
    while history and history[0] < now - LIMIT_WINDOW:
        history.pop(0)
    
    # 2. 检查是否超限
    if len(history) >= MAX_ATTEMPTS:
        logger.warning(f"安全警告: IP {client_ip} 触发激活码验证限流")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"尝试次数过多，请休息 {LIMIT_WINDOW} 秒后再试"
        )
    
    # 3. 记录本次请求
    history.append(now)
    return True


# --- 管理员认证 ---
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends
import secrets
from app.core.config import get_settings

security = HTTPBasic()

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    管理员认证依赖
    使用 HTTP Basic Auth
    """
    settings = get_settings()
    
    # 使用 secrets.compare_digest 防止时序攻击
    is_username_correct = secrets.compare_digest(
        credentials.username, settings.admin_username
    )
    is_password_correct = secrets.compare_digest(
        credentials.password, settings.admin_password
    )
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员认证失败",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
