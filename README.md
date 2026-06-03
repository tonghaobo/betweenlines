<<<<<<< HEAD
# BetweenLines（字里行间）

> Understand the vibe before you reply.

帮用户分析聊天状态，并给出自然回复建议，避免聊天翻车。

## 快速开始

详见 [本地启动指南](./docs/01-setup/本地启动指南.md)

## 技术栈

| 层级 | 技术 | 部署 |
|------|------|------|
| 前端 | Next.js 16 + TypeScript + Tailwind CSS v4 | Vercel |
| 后端 | FastAPI + Python 3.11 | Railway |
| AI | 豆包 API (Doubao / 火山引擎) | - |
| 存储 | SQLite (反馈 + 结果追踪 + 日志) | Railway Volume |

## 文档

| 文档 | 说明 |
|------|------|
| [项目概览](./docs/00-project-context/00-overview.md) | 定位、功能、产品原则 |
| [架构总览](./docs/00-project-context/01-architecture.md) | 整体架构图、数据流、设计决策 |
| [本地启动指南](./docs/01-setup/本地启动指南.md) | 环境配置、前后端启动 |
| [反馈闭环系统](./docs/02-architecture/feedback-loop.md) | 反馈采集、结果追踪、优化路线图 |
| [前端架构](./docs/03-frontend/README.md) | 组件树、状态管理、i18n |
| [后端架构](./docs/04-backend/README.md) | API、服务层、中间件 |
| [问题排查](./docs/05-troubleshooting/README.md) | 已知问题与解决方案 |
| [交付计划](./plans/) | 14天开发计划文档 |

## 产品原则

- ❌ 不做绝对判断（不说"她喜欢你"）
- ❌ 不代替用户聊天
- ❌ 不制造焦虑（禁止 PUA）
- ✅ 聊天记录默认不存储
- ✅ 输出自然、可发送
=======
# betweenlines
betweenlines project
>>>>>>> bde70797bd44a29db0c422ec78a03135b9b3ed35
