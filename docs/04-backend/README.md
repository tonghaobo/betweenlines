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
│   │   ├── doubao_service.py   # AI 服务（文本+视觉，多模型切换）
│   │   ├── chat_cleaner.py     # 输入清洗+安全检测
│   │   ├── chat_normalizer.py  # 聊天结构标准化（V2：自动解析参与者）
│   │   ├── usage_service.py    # 配额管理（V2：统一计数）
│   │   ├── cache.py            # 内容去重缓存（防刷新重复调 AI）
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
| `GET` | `/api/v1/usage` | 查询用户当日配额 | 无 |
| `POST` | `/api/v1/track` | 埋点事件上报 | 无 |
| `POST` | `/api/v1/share-reward` | 分享奖励领取 | 无 |
| `GET` | `/api/v1/metrics` | 数据指标面板 | 无 |

---

## 请求处理流程（以 analyze 为例）

```
POST /api/v1/analyze
    │
    ▼
[routers/chat.py] analyze_chat()
    │
    ├── 1. 内容缓存检查（cache.py）
    │   ├── SHA-256 哈希（内容+用户+关系类型）
    │   ├── 命中 → 直接返回缓存结果（0配额, 0 AI调用）
    │   └── 未命中 → 继续
    │
    ├── 2. 每日配额检查（usage_service.py）
    │   ├── analysis_used < FREE_DAILY_LIMIT → 允许
    │   └── 超限 → 429 daily_limit_reached
    │
    ├── 3. 输入验证
    │   ├── 长度检查: 10 ~ 2000 字符
    │   ├── 违规词检测: is_potentially_harmful()
    │   └── 格式验证: validate_chat_format()
    │
    ├── 4. 内容清洗
    │   └── clean_chat_content() → normalize_chat()
    │
    ├── 5. AI 分析
    │   └── DoubaoService.analyze_chat()
    │       ├── 构建精简 System Prompt (~90 chars)
    │       ├── 构建紧凑 User Prompt (一行 JSON schema)
    │       ├── 多模型切换（配额耗尽自动换下一个）
    │       ├── 调用豆包文本模型 (temperature=0.4)
    │       └── 解析 JSON → ChatAnalysisResponse
    │
    ├── 6. 写入缓存（10min TTL）
    │   └── set_cached_result()
    │
    ├── 7. 暂存分析结果（内存，用于后续 good_case 收集）
    │   └── _recent_analyses[user_id] = {features, analysis_json}
    │
    ├── 8. 记录日志
    │   └── save_analysis_log()
    │
    └── 9. 返回结果
        └── JSON Response
```

---

## 核心服务详解

### DoubaoService (`services/doubao_service.py`)

**System Prompt 结构**（V2 深度优化）：
- 角色定义：社交沟通分析专家
- 分析步骤（5步）：整体感知 → 双方对比 → 情绪识别 → 问题定位 → 综合判断
- 输出质量要求：每项字段的具体标准（如 analysis 必须有原文支撑）
- 禁止事项（6项）：判断喜欢、PUA、编造事实、模板化套话、替用户做决定、制造焦虑
- 输出格式：纯 JSON（禁止 markdown 包裹）

**Few-Shot 学习**：
- **静态示例**：2 个中英文对比示例（高质量 vs 低质量），嵌入式嵌入每次请求
- **动态学习**：用户点击 👍 时，自动提取特征并保存为 `good_cases`，后续分析按关系类型匹配注入
- **隐私安全**：仅存储统计特征（消息数、均长、问句比等），不存储聊天原文

**文本分析流程**：
```python
analyze_chat(chat_content: str) -> ChatAnalysisResponse
    1. _extract_chat_features(chat_content) → 特征预提取（纯 CPU, <1ms）
    2. _get_dynamic_fewshot(relationship_type) → 从 DB 加载用户认可案例
    3. _build_user_prompt(chat_content) → 融入静态+动态 few-shot 示例
    4. openai.chat.completions.create() → AI 调用
    5. _parse_response(response) → 解析 JSON + 类型强制转换容错
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

### 聊天标准化 (`services/chat_normalizer.py`)

**V2 新增**：自动解析任意格式的聊天输入。

| 功能 | 说明 |
|------|------|
| `normalize_chat(text)` | 识别"他/她/我"等格式，标准化聊天结构 |
| `extract_participants(text)` | 自动提取对话参与者标识 |
| `detect_wechat_style(text)` | 检测是否为微信风格的对话格式 |

支持直接粘贴微信聊天（不需要手动格式化），也兼容无格式纯文本。

### 配额管理 (`services/usage_service.py`)

**V2 统一配额**：文字分析和截图分析共享同一个每日限额（默认 10 次/天）。

**V1.3 多重奖励**：
- `_get_total_reward_count()` 合并分享 + 反馈奖励作为额外配额
- 分享奖励：`ENABLE_SHARE_REWARD` / `MAX_SHARE_REWARDS_PER_DAY`
- 反馈奖励：`ENABLE_FEEDBACK_REWARD` / `MAX_FEEDBACK_REWARDS_PER_DAY`

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

-- 反馈奖励表 (V1.3)
CREATE TABLE IF NOT EXISTS feedback_rewards (
    id TEXT PRIMARY KEY,
    anonymous_user_id TEXT NOT NULL,
    reward_date TEXT NOT NULL,
    reward_count INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
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

-- 优质案例表（V2 Few-Shot 学习，仅存特征不存原文）
CREATE TABLE IF NOT EXISTS good_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_hash TEXT NOT NULL,          -- SHA-256 特征去重
    total_messages INTEGER NOT NULL,
    total_rounds INTEGER NOT NULL,
    user_msgs INTEGER NOT NULL,
    other_msgs INTEGER NOT NULL,
    avg_user_len REAL NOT NULL,
    avg_other_len REAL NOT NULL,
    other_question_ratio REAL NOT NULL,
    notable_patterns TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    analysis_json TEXT NOT NULL,         -- AI 分析结果 JSON
    language TEXT DEFAULT 'zh',
    usage_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
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
| `save_good_case(features, relationship_type, analysis_json, language)` | 保存优质案例（仅特征，不含原文） |
| `get_good_cases(relationship_type, language, limit)` | 获取优质案例用于 Few-Shot 注入 |
| `_prune_good_cases(max_cases=100)` | 自动剪枝，超出上限删最旧记录 |

---

## 内容去重缓存 (`services/cache.py`)

防止用户刷新页面后重复提交相同内容导致浪费 AI token。

| 特性 | 值 |
|------|-----|
| 缓存键 | SHA-256(anonymous_user_id + relationship_type + chat_content) |
| TTL | 10 分钟 |
| 最大条目 | 100（超出自动清理过期） |
| 命中效果 | 跳过配额检查 + AI 调用，直接返回缓存结果 |

**集成位置**：`/analyze` 端点的第一步，在配额检查之前执行。

---

## 中间件

### 中间件执行顺序

CORS 中间件注册在最外层（最后 add），确保 OPTIONS 预检最先被处理：

```
请求 → CORS（最外层，处理 OPTIONS）→ 限流 → 安全头 → 路由
```

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
| `TEXT_MODELS` | `doubao-seed-2-0-mini-260428,...` | 文本模型列表（质量优先+速度加权排名，见 `tests/benchmark_models.py`） |
| `VISION_MODELS` | `doubao-1-5-vision-pro-32k-250115,...` | 视觉模型列表（同上，lite 不可用已移除） |
| `TEMPERATURE` | 0.4 | 文本温度（降低以提升分析一致性） |
| `MAX_TOKENS` | 700 | 文本最大 token（增加以容纳详细分析） |
| `VISION_TEMPERATURE` | 0.3 | OCR 温度（更保守） |
| `VISION_MAX_TOKENS` | 2000 | OCR 最大 token |
| `RATE_LIMIT_REQUESTS` | 20 | 每分钟请求数 |
| `MAX_CHAT_LENGTH` | 2000 | 最大输入长度 |
| `MIN_CHAT_LENGTH` | 10 | 最小输入长度 |
| `MAX_SCREENSHOTS_PER_REQUEST` | 3 | 单次最大截图数（累计，不可分批绕开） |
| `FREE_DAILY_LIMIT` | 10 | 每日免费分析次数 |
| `ENABLE_SHARE_REWARD` | true | 开启分享奖励 |
| `MAX_SHARE_REWARDS_PER_DAY` | 1 | 每日分享奖励上限 |
| `ENABLE_FEEDBACK_REWARD` | true | 开启反馈奖励（V1.3） |
| `MAX_FEEDBACK_REWARDS_PER_DAY` | 1 | 每日反馈奖励上限（V1.3） |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS 白名单（逗号分隔，生产需加 Vercel 域名） |
| `ALERT_WEBHOOK_URL` | - | 模型全部不可用时告警（支持 PushPlus/钉钉/飞书/企微） |

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

### MetricsResponse

```python
class MetricsResponse(BaseModel):
    dau: int                          # 日活
    d1_retention: float               # 次日留存率
    d7_retention: float               # 七日留存率
    total_analyses: int               # 总分析次数
    helpful_rate: float               # 有帮助率
    reply_adoption_rate: float        # 回复采纳率
    analysis_count_per_user: float    # 人均分析次数
    avg_analysis_duration_ms: int     # 平均分析耗时（毫秒）
    share_conversion_rate: float      # 分享转化率
    share_clicked_count: int          # 分享点击次数
    share_succeeded_count: int        # 分享成功次数
```

**访问方式**：前端 `/admin/metrics` 页面 → 调用 `GET /api/v1/metrics`

---

## 数据指标面板（Metrics Dashboard）

**路径**：`/admin/metrics`

**数据来源**：`GET /api/v1/metrics`（后端从 events 表聚合计算）

**展示指标**：

| 类别 | 指标 | 说明 |
|------|------|------|
| 用户 | DAU | 当日活跃用户数 |
| 留存 | D1 Retention | 次日回访率 |
| 留存 | D7 Retention | 七日后回访率 |
| 分析 | 总分析次数 | 成功分析总量 |
| 分析 | 有帮助率 | 用户认为有帮助的比例 |
| 分析 | 回复采纳率 | 用户使用了建议回复的比例 |
| 分析 | 人均分析次数 | 每个用户平均分析次数 |
| 分析 | 平均分析耗时 | 从提交到获得结果的平均时间 |
| 分享 | 分享转化率 | 分享成功 / 分享点击 |
| 分享 | 分享点击 | 分享按钮点击总次数 |
| 分享 | 分享成功 | 分享操作成功总次数 |

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
