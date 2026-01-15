# AI 亲子基因探测器 - 线上部署指南 (v1.0)

本指南针对 Linux 服务器（Ubuntu/Debian/CentOS）环境，介绍如何从零部署 AI 亲子基因探测器项目。

## 📋 1. 环境准备

### 1.1 系统要求
- **OS**: Ubuntu 22.04 LTS (推荐)
- **CPU/RAM**: 2核 4G+ (处理图片分析需要一定内存)
- **Disk**: 20GB+

### 1.2 基础软件安装
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-venv python3-pip nodejs npm nginx git

# 验证版本 (推荐 Python 3.10+, Node.js 18+)
python3 --version
node -v
```

### 1.3 获取代码
```bash
git clone <你的仓库地址> ai-gene-detector
cd ai-gene-detector
```

---

## 🐍 2. 后端部署 (FastAPI)

### 2.1 虚拟环境与依赖
```bash
cd backend
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install uvicorn[standard]  # 生产级服务器
```

### 2.2 环境变量配置
复制并在生产环境修改配置：
```bash
cp .env.example .env
nano .env
```
**必须修改的项**：
- `GEMINI_API_KEY`: 填写有效的 Google Gemini API Key。
- `ADMIN_PASSWORD`: 生产环境必须修改此密码！
- `CORS_ORIGINS`: 改为你的前端域名，例如 `https://your-domain.com`。
- `ENABLE_DOCS`: 生产环境建议设为 `false`。

### 2.3 初始化文件夹
```bash
mkdir -p data/temp
mkdir -p data/images
chmod 755 data
```

### 2.4 配置 Systemd 服务 (推荐)
创建服务文件 `/etc/systemd/system/backend.service`:
```ini
[Unit]
Description=AI Gene Detector Backend
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/ai-gene-detector/backend
Environment="PATH=/path/to/ai-gene-detector/backend/venv/bin"
ExecStart=/path/to/ai-gene-detector/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```
*注：请将 `/path/to/` 替换为实际路径。*

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start backend
sudo systemctl enable backend
```

---

## ⚛️ 3. 前端部署 (React)

### 3.1 编译构建
```bash
cd ../frontend
npm install

# 修改 API 地址 (如果后端不在同一域名下)
# 生产环境通常 Nginx 做反代，所以前端请求 /api 即可
npm run build
```
构建产物位于 `frontend/dist` 目录。

### 3.2 Nginx 配置 (HTTP + HTTPS)
生成配置文件 `/etc/nginx/sites-available/gene-detector`:

```nginx
server {
    listen 80;
    server_name your-domain.com; # 替换域名

    # 前端静态文件
    location / {
        root /path/to/ai-gene-detector/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 允许大文件上传 (图片)
        client_max_body_size 20M;
    }
}
```

启用站点并重启 Nginx：
```bash
sudo ln -s /etc/nginx/sites-available/gene-detector /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 4. 生产环境安全检查

1.  **SSL 证书**：强烈建议配置 HTTPS (使用 Certbot)。
    ```bash
    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d your-domain.com
    ```
2.  **防火墙**：仅开放 80, 443 和 SSH 端口。
    ```bash
    sudo ufw allow 'Nginx Full'
    sudo ufw allow OpenSSH
    sudo ufw enable
    ```
3.  **定期备份**：定期备份 `backend/data/app.db` 数据库文件。

## 🛠 5. 常用维护命令

- **查看后端日志**: `journalctl -u backend -f`
- **重启后端**: `sudo systemctl restart backend`
- **重启前端(Nginx)**: `sudo systemctl restart nginx`
- **批量生成激活码**:
  ```bash
  # 使用 curl 调用管理接口 (需 Base64 编码的 admin:password)
  curl -X POST http://localhost:8000/api/code/batch-create \
    -H "Authorization: Basic <Base64_Credentials>" \
    -d '{"codes": ["VIP001", "VIP002"]}'
  ```

---
*文档生成时间：2026-01-15*
