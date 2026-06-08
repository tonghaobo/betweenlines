# BetweenLines 项目文档

> 本目录为项目核心文档，供 AI 模型或新开发者快速理解项目全貌。

## 文档索引

| 文档 | 用途 | 阅读时间 |
|------|------|----------|
| [项目概览](./00-overview.md) | 一句话定位、技术栈、产品原则 | 2 min |
| [架构总览](./01-architecture.md) | 整体架构图、数据流、分层设计 | 5 min |
| [本地启动指南](../01-setup/本地启动指南.md) | 环境配置、前后端启动、局域网测试 | 5 min |
| [容器部署指南](../01-setup/容器部署指南.md) | Docker 构建、compose 编排、数据持久化 | 5 min |
| [反馈闭环系统](../02-architecture/feedback-loop.md) | 反馈采集、结果追踪、标签化、Prompt优化路线图 | 5 min |
| [前端架构详解](../03-frontend/README.md) | 组件树、路由、状态管理、i18n | 10 min |
| [后端架构详解](../04-backend/README.md) | API 路由、服务层、中间件、数据库 | 10 min |
| [问题排查](../05-troubleshooting/README.md) | 已知问题与解决方案 | 3 min |

## 目录结构

```
docs/
├── 00-project-context/     # 项目概览与架构
│   ├── 00-overview.md      # 项目概览
│   ├── 01-architecture.md  # 架构总览
│   └── README.md           # 文档索引
├── 01-setup/               # 环境搭建
│   ├── 本地启动指南.md     # 本地启动文档
│   └── 容器部署指南.md     # Docker 容器部署
├── 02-architecture/        # 架构深入
│   └── feedback-loop.md    # 反馈闭环系统设计
├── 03-frontend/            # 前端文档
│   └── README.md           # 前端架构详解
├── 04-backend/             # 后端文档
│   └── README.md           # 后端架构详解
└── 05-troubleshooting/     # 问题排查
    └── README.md           # 已知问题与解决方案
```
