# AI 娱乐 - 孩子像谁

基于 Google Gemini AI 的亲子面部特征分析 H5 应用。

## 📁 项目结构

```
AI-Gene-Detector/
├── frontend/          # React + Vite 前端
├── backend/           # Python FastAPI 后端
└── designed.md        # 产品设计文档
```

## 🚀 快速开始

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填写 GEMINI_API_KEY

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 创建测试兑换码

```bash
# 调用管理接口创建兑换码
curl -X POST http://localhost:8000/api/code/batch-create \
  -H "Content-Type: application/json" \
  -d '{"codes": ["TEST0001", "TEST0002", "TEST0003"]}'
```

## 📖 功能说明

1. **首页**: 输入兑换码激活服务
2. **上传页**: 上传父母和孩子的照片
3. **分析页**: AI 正在分析中的加载动画
4. **结果页**: 展示带有面部标注的分析结果图

## 🔧 技术栈

- **前端**: React 18 + Vite + Tailwind CSS v4 + Framer Motion
- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **AI**: Google Gemini 2.0 Flash

## 📝 License

MIT
