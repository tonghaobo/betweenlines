# 架构总览

## 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户浏览器                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Next.js App (localhost:3000)                  │  │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────────────────┐   │  │
│  │  │ layout  │  │  page    │  │   I18nLayout            │   │  │
│  │  │ (Server)│  │ (Client) │  │   ┌──────────────────┐ │   │  │
│  │  │         │  │          │  │   │  I18nProvider     │ │   │  │
│  │  │  ───────│──│──────────│──│───│  ┌─────────────┐ │ │   │  │
│  │  │         │  │          │  │   │  │ LangSwitcher │ │ │   │  │
│  │  │         │  │ Hero     │  │   │  │ (fixed 右上) │ │ │   │  │
│  │  │         │  │ ChatInput│  │   │  └─────────────┘ │ │   │  │
│  │  │         │  │ Result   │  │   │  {children}      │ │   │  │
│  │  │         │  │ Feedback │  │   │  └──────────────────┘ │   │  │
│  │  └─────────┘  └──────────┘  └────────────────────────┘   │  │
│  │                                                           │  │
│  │  lib/                                                     │  │
│  │  ├── api.ts        (API 调用 + 超时 + 重试)                │  │
│  │  ├── useChatAnalysis.ts  (状态管理 Hook)                   │  │
│  │  └── cache.ts      (客户端缓存)                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         │ /api/:path* (dev: rewrite)          │ NEXT_PUBLIC_API_URL (prod)
         ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FastAPI Server (localhost:8000)                  │
│                                                                  │
│  main.py                                                        │
│  ├── CORS Middleware      (ALLOWED_ORIGINS 白名单)              │
│  ├── Security Middleware  (CSP / X-Frame / HSTS)               │
│  ├── Rate Limit           (20 req/min, /api/v1/analyze)        │
│  │                                                               │
│  ├── GET  /health          → 健康检查                           │
│  ├── POST /api/v1/analyze  → 聊天分析                           │
│  ├── POST /api/v1/analyze-screenshot → 截图OCR                  │
│  ├── POST /api/v1/feedback → 用户反馈（含原因+评论）            │
│  ├── POST /api/v1/outcome  → 结果追踪                           │
│  └── GET  /api/v1/stats    → 反馈+结果统计                      │
│                                                                  │
│  routers/chat.py                                               │
│  ├── 输入验证 (长度/格式/违规词)                                 │
│  ├── 内容清洗 (clean_chat_content)                              │
│  └── 调用 DoubaoService                                        │
│                                                                  │
│  services/                                                     │
│  ├── doubao_service.py  → AI 调用 (文本 + 视觉)                 │
│  ├── chat_cleaner.py    → 输入清洗 + 安全检测                   │
│  └── storage.py         → SQLite 存储                           │
│                                                                  │
│  schemas/chat.py        → Pydantic 请求/响应模型                │
└─────────────────────────────────────────────────────────────────┘
         │
         │ OpenAI 兼容协议
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              火山引擎 ARK (豆包 API)                             │
│                                                                  │
│  doubao-seed-1-8-251228   (文本分析模型)                        │
│  doubao-vision-pro-32k    (截图 OCR 多模态模型)                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SQLite (Railway Volume)                       │
│                                                                  │
│  feedback 表        → 用户反馈 (helpful + reason + comment)     │
│  outcome 表         → 结果追踪 (reply_used + outcome)           │
│  analysis_log 表    → 分析日志 (长度/状态/耗时/错误)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据流

### 主流程：聊天分析

```
用户输入聊天记录
    │
    ▼
[前端] page.tsx: handleSubmit()
    │
    ▼
[前端] lib/api.ts: analyzeChat()
    ├── 超时控制 (AbortController, 30s)
    ├── 自动重试 (指数退避, 最多 2 次)
    └── 响应验证 (chat_status + reply_suggestions)
    │
    ▼
[后端] routers/chat.py: POST /api/v1/analyze
    ├── 输入验证 (10~5000 字符)
    ├── 违规词检测 (is_potentially_harmful)
    ├── 内容清洗 (clean_chat_content)
    └── 格式验证 (validate_chat_format)
    │
    ▼
[后端] services/doubao_service.py: analyze_chat()
    ├── 构建 System Prompt (角色 + 分析重点 + 禁止事项)
    ├── 构建 User Prompt (聊天内容 + JSON Schema)
    ├── 调用豆包文本模型
    └── 解析 JSON 响应 → ChatAnalysisResponse
    │
    ▼
[前端] lib/useChatAnalysis.ts: analyze()
    ├── 设置 isLoading = true
    ├── 成功 → 设置 result
    └── 失败 → 设置 error + errorType
    │
    ▼
[前端] page.tsx 根据状态渲染
    ├── isLoading  → LoadingOverlay
    ├── result     → ResultPage + FeedbackSection + ReplyAdoptionCard
    └── error      → 错误提示
```

### 反馈闭环流程

```
[结果页] FeedbackSection: 👍/👎 + 原因选择 + 评论
    │
    ▼
[前端] api.ts: submitFeedback(helpful, analysisId, reason, comment)
    │
    ▼
[后端] POST /api/v1/feedback → feedback 表

[结果页] ReplyAdoptionCard: 发了/没发/改了一下再发
    │
    ▼
[前端] api.ts: submitOutcome(replyUsed)
    │
    ▼
[后端] POST /api/v1/outcome → outcome 表

[首页 24h后] FollowUpReminder: 回复更积极/差不多/更冷淡/没回复/不想说
    │
    ▼
[前端] api.ts: submitOutcome("sent", outcome)
    │
    ▼
[后端] POST /api/v1/outcome → outcome 表
```

---

## 关键设计决策

### 1. 为什么用豆包而非 OpenAI？

- 国内用户访问速度更快
- 火山引擎 ARK 提供 OpenAI 兼容 API，迁移成本低
- 豆包对中文场景理解更好

### 2. 为什么 SQLite 而非 PostgreSQL？

- V1 阶段数据量极小（仅反馈和日志）
- 零配置，降低运维复杂度
- Railway Volume 提供持久化存储

### 3. 为什么 i18n 用 Context 而非 next-intl？

- V1 仅中英两种语言，Context 足够轻量
- 避免额外依赖
- 服务端渲染安全（首次渲染固定 en，客户端恢复用户选择）

### 4. 为什么截图 OCR 分两步？

- 先提取文字 → 用户确认 → 再分析
- 避免 OCR 识别错误导致分析偏差
- 用户体验更好（可以修正识别结果）

### 5. 为什么前端直接调后端而非走 Next.js API Route？

- Next.js rewrite 在 dev 模式做代理，避免 CORS 问题
- 生产环境前端直连后端，减少中间层
- 后端独立部署，架构更清晰

### 6. 为什么反馈系统分 Phase 渐进实现？

- Phase 1-2 先建立数据闭环（反馈采集 + 结果追踪）
- Phase 3-5 基于真实数据再优化（标签化 + Prompt 优化 + 相似案例）
- 避免在数据不足时过度设计
