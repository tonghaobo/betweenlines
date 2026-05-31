# Chat Coach（聊天教练）

> Understand the vibe before you reply.

帮用户分析聊天状态，并给出自然回复建议，避免聊天翻车。

## 技术栈

| 层级 | 技术 | 部署 |
|------|------|------|
| 前端 | Next.js 16 + TypeScript + Tailwind CSS v4 | Vercel |
| 后端 | FastAPI + Python 3.11 | Railway |
| AI | 豆包 API (Doubao-pro-32k / 火山引擎) | - |
| 存储 | SQLite (V1 反馈数据) | Railway Volume |

## 本地开发

### 前置条件
- Node.js 18+
- Python 3.11+
- 豆包 API Key（火山引擎）

### 启动后端
```bash
cd backend
# 编辑 .env 填入你的豆包 API Key
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 启动前端
```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### 运行测试
```bash
cd backend
python tests/test_api.py
```

## 部署

### 前端 → Vercel
```bash
cd frontend
vercel --prod
```

### 后端 → Railway
1. 连接 GitHub 仓库
2. 设置 Root Directory 为 `backend`
3. 添加环境变量 `OPENAI_API_KEY`（豆包 API Key）和 `OPENAI_BASE_URL`
4. 部署

## 产品原则

- ❌ 不做绝对判断（不说"她喜欢你"）
- ❌ 不代替用户聊天
- ❌ 不制造焦虑（禁止 PUA）
- ✅ 聊天记录默认不存储
- ✅ 输出自然、可发送

## 项目结构

```
chatvibe/
├── frontend/          # Next.js 前端
│   └── src/
│       ├── app/       # 页面路由
│       ├── components/# UI 组件
│       └── lib/       # 工具函数 & Hooks
├── backend/           # FastAPI 后端
│   └── app/
│       ├── routers/   # API 路由
│       ├── services/  # 业务逻辑
│       ├── schemas/   # 数据模型
│       ├── middleware/ # 中间件
│       └── core/      # 配置
└── plans/             # 交付计划文档
```
