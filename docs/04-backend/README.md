# 后端架构详解

## 技术栈

- **框架**：FastAPI + Uvicorn
- **语言**：Python 3.11
- **数据验证**：Pydantic v2
- **AI SDK**：OpenAI Python SDK（兼容豆包 API）
- **存储**：SQLite（同步 sqlite3）
- **部署**：Railway（Procfile + runtime.txt）

---

## 目录结构

```
backend/
├── .env                   # 环境变量（gitignore）
├── Procfile               # Railway 启动命令
├── runtime.txt            # Python 版本声明
├── requirements.txt       # 依赖清单
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── core/
│   │   └── config.py      # 配置管理（pydantic-settings）
│   ├── routers/
│   │   └── chat.py        # API 路由（6 个端点）
│   ├── services/
│   │   ├── doubao_service.py   # AI 服务（文本+视觉）
│   │   ├── chat_cleaner.py     # 输入清洗+安全检测
│   │   └── storage.py          # SQLite 存储
│   ├── schemas/
│   │   └── chat.py        # Pydantic 请求/响应模型
│   └── middleware/
│       ├── rate_limit.py  # IP 限流
│       └── security.py    # 安全头
└── tests/
    ├── test_api.py        # API 集成测试
    ├── test_prompt.py     # Prompt 效果测试
    └── test_production.py # 生产环境验证
```

---

## API 端点

| 方法 | 路径 | 功能 | 限流 |
|------|------|------|------|
| `GET` | `/health` | 健康检查 | 无 |
| `POST` | `/api/v1/analyze` | 聊天分析 | 20次/分钟 |
| `POST` | `/api/v1/analyze-screenshot` | 截图OCR | 无 |
| `POST` | `/api/v1/feedback` | 用户反馈（含原因+评论） | 无 |
| `POST` | `/api/v1/outcome` | 结果追踪 | 无 |
| `GET` | `/api/v1/stats` | 反馈+结果统计 | 无 |

---

## 请求处理流程（以 analyze 为例）

```
POST /api/v1/analyze
    │
    ▼
[routers/chat.py] analyze_chat()
    │
    ├── 1. 输入验证
    │   ├── 长度检查: 10 ~ 5000 字符
    │   ├── 违规词检测: is_potentially_harmful()
    │   └── 格式验证: validate_chat_format()
    │
    ├── 2. 内容清洗
    │   └── clean_chat_content()
    │       ├── 去首尾空白
    │       ├── 规范化换行 (\r\n → \n)
    │       └── 移除多余空行
    │
    ├── 3. AI 分析
    │   └── DoubaoService.analyze_chat()
    │       ├── 构建 System Prompt (角色+规则)
    │       ├── 构建 User Prompt (聊天内容+JSON Schema)
    │       ├── 调用豆包文本模型 (temperature=0.7)
    │       └── 解析 JSON → ChatAnalysisResponse
    │
    ├── 4. 记录日志
    │   └── save_analysis_log()
    │       └── INSERT INTO analysis_log (长度/状态/耗时/错误)
    │
    └── 5. 返回结果
        └── JSON Response
```

---

## 核心服务详解

### DoubaoService (`services/doubao_service.py`)

**System Prompt 结构**：
- 角色定义：专业社交沟通分析助手
- 分析重点（6项）：互动温度、回复意愿、聊天节奏、潜在风险、关系状态、最佳策略
- 禁止事项（5项）：不做绝对判断、不代替聊天、不制造焦虑、不输出PUA内容、不评判用户
- 回复规则（4条）：自然流畅、风格多样、正向建议、可直接发送
- 输出格式：严格 JSON Schema

**文本分析流程**：
```python
analyze_chat(chat_content: str) -> ChatAnalysisResponse
    1. _build_user_prompt(chat_content) → 带 JSON Schema 的 User Prompt
    2. openai.chat.completions.create() → AI 调用
    3. _parse_response(response) → 解析 JSON，清理 Markdown 代码块标记
```

**截图 OCR 流程**：
```python
extract_text_from_screenshot(image_bytes: bytes) -> ScreenshotAnalysisResponse
    1. 将图片 bytes 转为 base64
    2. 构建 data:image/xxx;base64,xxx URL
    3. 调用 doubao-vision-pro-32k 多模态模型
    4. 提取文字，按 A/B 格式区分发言人
```

### 内容清洗 (`services/chat_cleaner.py`)

| 函数 | 作用 |
|------|------|
| `clean_chat_content()` | 去空白、规范化换行、去多余空行 |
| `validate_chat_format()` | 检测对话格式，返回警告（不阻止） |
| `is_potentially_harmful()` | 关键词黑名单检测（PUA、把妹、泡妞等） |

### 数据存储 (`services/storage.py`)

**表结构**：

```sql
-- 反馈表
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    helpful BOOLEAN NOT NULL,
    analysis_id TEXT,
    reason TEXT DEFAULT '',       -- 反馈原因（逗号分隔）
    comment TEXT DEFAULT '',      -- 用户补充文字
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 结果追踪表
CREATE TABLE IF NOT EXISTS outcome (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT,
    reply_used TEXT,              -- sent / not_sent / modified
    outcome TEXT,                 -- more_positive / about_same / colder / no_reply / prefer_not
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 分析日志表
CREATE TABLE IF NOT EXISTS analysis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_length INTEGER NOT NULL,
    chat_status TEXT,
    request_duration_ms REAL,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**存储函数**：

| 函数 | 作用 |
|------|------|
| `save_feedback(helpful, analysis_id, reason, comment)` | 保存反馈 |
| `get_feedback_stats()` | 返回 total / helpful / helpful_rate |
| `save_outcome(analysis_id, reply_used, outcome)` | 保存结果追踪 |
| `get_outcome_stats()` | 返回 reply_adoption_rate / positive_outcome_rate |
| `save_analysis_log(chat_length, chat_status, duration_ms, error)` | 保存分析日志 |

---

## 中间件

### 限流 (`middleware/rate_limit.py`)

- 算法：滑动窗口
- 维度：按 IP
- 作用范围：仅 `/api/v1/analyze`
- 配置：`RATE_LIMIT_REQUESTS=20`，`RATE_LIMIT_WINDOW=60`（20次/分钟）
- 超限返回：429 Too Many Requests

### 安全头 (`middleware/security.py`)

| Header | Value |
|--------|-------|
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| X-XSS-Protection | 1; mode=block |
| Content-Security-Policy | default-src 'self' |
| Referrer-Policy | strict-origin-when-cross-origin |
| Strict-Transport-Security | max-age=31536000; includeSubDomains |

---

## 配置管理 (`core/config.py`)

使用 `pydantic-settings` 的 `BaseSettings`，自动从 `.env` 文件和系统环境变量加载。

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | - | **必填**，豆包 API Key |
| `OPENAI_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | API 地址 |
| `OPENAI_MODEL` | `doubao-seed-1-8-251228` | 文本模型 |
| `VISION_MODEL` | `doubao-vision-pro-32k` | 视觉模型 |
| `TEMPERATURE` | 0.7 | 文本温度 |
| `MAX_TOKENS` | 1000 | 文本最大 token |
| `VISION_TEMPERATURE` | 0.3 | OCR 温度（更保守） |
| `VISION_MAX_TOKENS` | 2000 | OCR 最大 token |
| `RATE_LIMIT_REQUESTS` | 20 | 每分钟请求数 |
| `MAX_CHAT_LENGTH` | 5000 | 最大输入长度 |
| `MIN_CHAT_LENGTH` | 10 | 最小输入长度 |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS 白名单（逗号分隔） |

---

## 数据模型（Schemas）

### ChatStatus 枚举

| 值 | 中文 | 颜色 |
|----|------|------|
| `POSITIVE` | 积极互动 | 绿色 |
| `NORMAL` | 普通互动 | 蓝色 |
| `POLITE` | 礼貌回应 | 黄色 |
| `COLD` | 偏冷淡 | 橙色 |
| `RISKY` | 对话风险较高 | 红色 |

### ChatAnalysisResponse

```python
class ChatAnalysisResponse(BaseModel):
    chat_status: str        # ChatStatus 枚举值
    analysis: str           # 分析文本
    issues: List[str]       # 改进建议列表
    risks: List[str]        # 风险提醒列表
    reply_suggestions:      # 三种风格回复
        natural: str
        humorous: str
        mature: str
    timing_advice: str      # 回复时机建议
```

### FeedbackRequest

```python
class FeedbackRequest(BaseModel):
    analysis_id: Optional[str]   # 分析记录ID
    helpful: bool                # 是否有帮助
    reason: list[str]            # 反馈原因
    comment: str                 # 补充文字
```

### OutcomeRequest

```python
class OutcomeRequest(BaseModel):
    analysis_id: Optional[str]   # 分析记录ID
    reply_used: str              # sent / not_sent / modified
    outcome: str                 # more_positive / about_same / colder / no_reply / prefer_not
```

---

## 测试

### test_api.py

- 12 个聊天场景：积极互动、普通互动、冷淡、礼貌、高风险、初次搭话、对方主导、久未联系、单方面输出、微信风格、中英混合、深夜对话
- 5 个边界条件：空输入、超长、违规内容、纯空白、单人聊天
- 3 个杂项：正向/负向反馈、统计查询、健康检查

### test_prompt.py

直接调用 OpenAI SDK（绕过 FastAPI），测试 4 个场景的 AI 分析质量。

### test_production.py

生产环境验证：健康检查、CORS 预检、分析接口、速率限制。
