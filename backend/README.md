# AI 亲子基因探测器 - 后端

基于 Python FastAPI 的轻量级后端服务。

## 技术栈

- **框架**: FastAPI (异步高性能)
- **数据库**: SQLite + SQLAlchemy (异步)
- **AI**: Google Gemini API
- **定时任务**: APScheduler

## 快速开始

### 1. 创建虚拟环境

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写你的 Gemini API Key
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API 接口

### 验证兑换码
```
POST /api/code/verify
Body: { "code": "ABC12345", "device_id": "fp_xxx" }
```

### 上传分析照片
```
POST /api/analyze
Headers: Authorization: Bearer <兑换码>
Body: multipart/form-data (child, father, mother)
```

### 获取缓存结果
```
GET /api/analyze/result
Headers: Authorization: Bearer <兑换码>
```

### 批量创建兑换码（管理）
```
POST /api/code/batch-create
Body: { "codes": ["CODE001", "CODE002", ...] }
```

## 目录结构

```
backend/
├── app/
│   ├── api/           # API 路由
│   │   ├── code.py    # 兑换码接口
│   │   └── analyze.py # 分析接口
│   ├── core/          # 核心配置
│   │   ├── config.py  # 环境配置
│   │   └── database.py# 数据库连接
│   ├── models/        # 数据模型
│   │   └── card_key.py# 兑换码模型
│   ├── services/      # 业务服务
│   │   ├── gemini_service.py  # Gemini AI
│   │   └── scheduler.py       # 定时任务
│   └── main.py        # 应用入口
├── data/              # 数据目录
│   ├── app.db         # SQLite 数据库
│   └── temp/          # 临时文件
├── requirements.txt   # 依赖
└── .env.example       # 环境变量模板
```

## 生产部署

推荐使用 Supervisor 或 systemd 管理进程：

```bash
# 使用 gunicorn + uvicorn worker
pip install gunicorn
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

对于低配服务器，1-2 个 worker 即可。
