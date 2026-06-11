# 前端架构详解

## 技术栈

- **框架**：Next.js 16 (App Router) + React 19
- **语言**：TypeScript
- **样式**：Tailwind CSS v4（`@import "tailwindcss"` 方式引入，`@theme` 定义自定义动画）
- **状态管理**：React Context（i18n）+ 自定义 Hook（useChatAnalysis）
- **HTTP**：原生 `fetch` + AbortController（超时控制）+ 指数退避重试

---

## 目录结构

```
frontend/src/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx          # 根布局 (Server Component)
│   ├── page.tsx            # 首页 (Client Component)
│   ├── I18nLayout.tsx      # 国际化布局包装器
│   ├── globals.css         # Tailwind + 自定义样式
│   ├── robots.ts           # SEO robots.txt
│   ├── sitemap.ts          # SEO sitemap
│   └── admin/
│       └── metrics/
│           └── page.tsx    # 数据指标面板 → 访问 /admin/metrics
├── components/             # UI 组件
│   ├── hero/               # 首页 Hero 区域
│   │   ├── HeroSection.tsx      # Hero（V2：单行标题 + 双CTA）
│   │   └── ExampleChats.tsx     # 示例聊天按钮（V2 已由 DemoAnalysis 替代）
│   ├── home/               # 首页 V2 新增组件
│   │   ├── DemoAnalysis.tsx     # Demo 分析展示（聊天气泡 + 分析结果双卡片）
│   │   ├── FeaturesSection.tsx  # 用户收益卡片（3张）
│   │   └── SocialProof.tsx      # 早期用户反馈展示
│   ├── chat-input/         # 输入框（V2：统一入口）
│   │   ├── InputBox.tsx            # 统一输入组件（隐私提示 + Demo填充）
│   │   ├── ChatInput.tsx           # [已弃用] 旧双模式输入
│   │   └── RelationshipSelector.tsx # 关系类型选择器
│   ├── result/             # 分析结果
│   │   ├── ResultPage.tsx       # 结果页容器
│   │   ├── StatusBadge.tsx      # 状态标签 (5种)
│   │   ├── AnalysisCard.tsx     # 分析详情
│   │   ├── ReplySuggestions.tsx # 回复建议网格
│   │   ├── ReplyCard.tsx        # 单个回复卡片 (含复制)
│   │   └── TimingAdvice.tsx     # 节奏建议
│   ├── feedback/           # 反馈与追踪
│   │   ├── FeedbackSection.tsx    # 👍/👎 + 原因选择 + 评论
│   │   ├── ReplyAdoptionCard.tsx  # 回复采用率采集
│   │   └── FollowUpReminder.tsx   # 24h 后回访浮层
│   ├── share/              # 分享功能
│   │   ├── ShareButton.tsx      # 分享按钮 + 平台选择面板
│   │   └── ShareCard.tsx        # 分享卡片渲染 (被截图)
│   └── ui/                 # 通用 UI
│       ├── LangSwitcher.tsx     # 语言切换按钮
│       ├── LoadingOverlay.tsx   # 加载动画
│       ├── SkeletonCard.tsx     # 骨架屏
│       └── UsageLimitModal.tsx  # 配额耗尽弹窗
├── lib/                    # 工具库
│   ├── api.ts              # API 调用层 (超时/重试/错误处理)
│   ├── useChatAnalysis.ts  # 分析状态管理 Hook (含 sessionStorage 持久化)
│   ├── analytics.ts        # 埋点 SDK (匿名ID + 事件上报)
│   └── cache.ts            # 客户端缓存
├── contexts/               # React Context
│   └── I18nContext.tsx     # 国际化 (中/英)
└── locales/                # 翻译文案
    ├── types.ts            # 类型定义
    ├── en.ts               # 英文文案
    └── zh.ts               # 中文文案
```

---

## 组件树（V2 首页结构）

```
<html lang="en" suppressHydrationWarning>
  <body>
    <I18nLayout>                           ← Client Component
      <I18nProvider>                       ← Context Provider
        <LangSwitcher />                   ← 固定右上角，z-[9999]
        <main>
          <Home>                           ← Client Component
            ├── 正常状态 (V2 首页结构)
            │   ├── <HeroSection />        ← 新文案 + 双CTA（免费试一次/看看效果）
            │   ├── <DemoAnalysis />       ← 聊天气泡 + 分析结果双卡片展示
            │   ├── <InputBox />           ← 统一输入（隐私提示 + Demo一键填充）
            │   ├── <FeaturesSection />    ← 3张用户收益卡片
            │   ├── <SocialProof />        ← 早期用户反馈
            │   ├── <FollowUpReminder />   ← 24h后回访浮层 (条件显示)
            │   └── 错误提示 (如有)
            ├── Loading 状态
            │   ├── <HeroSection />
            │   ├── <InputBox isLoading />
            │   └── <LoadingOverlay />
            └── 结果状态
                ├── 返回按钮
                ├── <ResultPage />
                │   ├── <StatusBadge />
                │   ├── <AnalysisCard />
                │   ├── <ReplySuggestions />
                │   │   └── <ReplyCard /> × 3 (自然/幽默/成熟)
                │   └── <TimingAdvice />
                ├── <FeedbackSection />       ← 👍/👎 + 原因选择
                └── <ReplyAdoptionCard />     ← 回复采用率
```

### V2 首页转化优化（Landing Page V2）

页面结构从 `Hero → ExampleChats → Input → FollowUp` 重构为：

```
Hero (强价值 + CTA)
↓
DemoAnalysis (立即展示产品价值)
↓
Input (隐私提示 + Demo填充 + 一键分析)
↓
Features (用户收益，非工具描述)
↓
SocialProof (早期用户反馈)
```

Hero 改动：
- 标题：单行 `"Read what's not being said."` / `"看懂聊天里的潜台词"`
- 新增双 CTA：`"免费试一次"`（→ 输入区） / `"看看分析效果"`（→ #demo-analysis）
- 移除内联 features checkmarks（移至 FeaturesSection）

InputBox 改动：
- 新增隐私提示：`"🔒 默认不保存聊天记录，分析后自动删除"`
- 新增 `"试试示例聊天"` 按钮：一键填充 demo 聊天 + 自动触发分析
- Placeholder 优化：带示例格式的引导文案

新增埋点：`hero_cta_clicked` / `demo_cta_clicked` / `demo_used` / `first_analysis_started` / `first_analysis_success` / `bounce_under_10s`

---

## 核心交互流程

### V2 统一输入流程

```
1. 用户在 InputBox 粘贴聊天文字 / 截图 / 图片（统一入口，无需选择模式）
2. 系统自动识别输入类型：
   ├── 纯文本 → 直接分析
   └── 图片 → 自动 OCR 提取文字
3. OCR 提取后显示文字确认，支持"继续添加截图"追加更多对话
4. 确认分析 → page.tsx: handleSubmit() → useChatAnalysis.analyze()
5. api.ts: analyzeChat() 发送 POST 请求
   ├── 30s 超时
   ├── 失败自动重试 2 次
   └── 验证响应格式
6. 成功 → result 更新，切换到结果视图
7. 结果显示状态标签、分析详情、回复建议、节奏建议
8. 用户可复制回复、提交反馈（👍/👎）、标记是否采用

### 输入方式支持

| 方式 | 支持 | 说明 |
|------|------|------|
| 粘贴微信聊天文字 | ✅ | 无需手动格式化，AI 自动识别 |
| 粘贴截图（⌘V） | ✅ | 直接从剪贴板粘贴图片 |
| 拖拽图片 | ✅ | 支持多张同时拖入 |
| 点击上传 | ✅ | 文件选择器兜底 |
| 继续添加截图 | ✅ | 提取文字后可按需追加更多截图 |

### 反馈闭环流程

```
1. 结果页底部: FeedbackSection
   ├── 点击 👍 → 弹出正反馈原因多选 (态度分析/回复建议/节奏建议/风险提醒/很真实) + 评论
   └── 点击 👎 → 弹出负反馈原因多选 (不够准确/太尴尬/太泛/不适合/看不懂/其他) + 评论
2. 结果页底部: ReplyAdoptionCard
   └── 单选: 发了 / 没发 / 改了一下再发
3. 首页 24h 后: FollowUpReminder (底部浮层)
   └── 单选: 回复更积极 / 差不多 / 更冷淡 / 没回复 / 不想说
```

---

## 状态管理

### useChatAnalysis Hook

```typescript
{
  result: ChatAnalysisResponse | null,  // 分析结果
  isLoading: boolean,                    // 加载中
  error: string | null,                  // 错误信息
  errorType: "validation" | "timeout" | "network" | "server" | "rate_limit" | null,
}
```

- `analyze(content)` → 触发分析
- `reset()` → 回到首页

**sessionStorage 持久化（V1.2）**：
- 分析成功后自动保存到 `sessionStorage`（30 分钟 TTL）
- 刷新页面时自动恢复结果，无需重新分析
- OCR 文字也持久化到 `sessionStorage`，刷新不丢

### 截图上传计数

- 使用 `screenshotCountRef`（useRef）保证异步 OCR 中计数的正确性
- 累计计数持久化到 `sessionStorage`，刷新后接续计数
- 后端 + 前端双重限制（`MAX_SCREENSHOTS_PER_REQUEST`）

### 关系类型选择

- `relationshipType` 状态提升到 `page.tsx`，避免 InputBox 卸载/重挂载后重置为默认值
- 选择非恋爱标签后分析，返回首页时保持选择不变

### 分享 & 反馈奖励提示

- 主页用量区显示分享奖励提示（有剩余/已用完两种状态）
- 提交反馈后显示 `+1 次分析已到账！` 动画提示
- 完成后自动刷新用量显示

### 文本框 & OCR 交互

- textarea 在分析过程中始终可编辑（移除 `disabled={isLoading}`）
- 有文字时上传截图 → OCR 结果自动追加到文本框末尾（`---` 分隔）
- 分隔符在送模型前自动清洗（page.tsx handleSubmit）
- 手动输入的文字通过 `sessionStorage` 持久化，刷新后恢复
- OCR 提取文字改为可编辑 textarea（替换只读 div）

### I18nContext

- `locale`: `"en" | "zh"`
- `t`: 当前语言的翻译对象
- `toggleLocale()`: 切换语言
- `setLocale(key)`: 设置指定语言
- 持久化：`localStorage("betweenlines-locale")` + 内存 fallback

---

## 国际化策略

1. **SSR 安全**：首次渲染固定为 `en`，客户端 `useEffect` 挂载后恢复用户选择
2. **hydration 安全**：`mounted` 标志位，挂载前始终用 `en` 渲染
3. **localStorage 容错**：检测可用性，不可用时使用内存 fallback
4. **类型安全**：`zh.ts` 通过 `satisfies typeof en` 约束，保证中英文 key 完全一致

---

## API 调用层 (lib/api.ts)

| 功能 | 函数 | 超时 | 重试 |
|------|------|------|------|
| 聊天分析 | `analyzeChat()` | 30s | 2次 |
| 截图OCR | `analyzeScreenshot()` | 300s | 2次 |
| 提交反馈 | `submitFeedback(helpful, analysisId?, reason?, comment?)` | 5s | 无 |
| 提交结果 | `submitOutcome(replyUsed, outcome?, analysisId?)` | 5s | 无 |

**错误分类**：
- `ApiError` 类：statusCode / isTimeout / isNetworkError
- 400 → 不重试（输入错误）
- 429 → 不重试（限流）
- 超时 → 提示"请求超时"
- 网络错误 → 提示"网络错误"

**`analytics.ts` 请求路径**：
- 研发模式 API_BASE_URL 为空（走 Next.js rewrite，同源无 CORS）
- 生产模式通过 `NEXT_PUBLIC_API_URL` 直连 Railway 后端
- 请求失败无声降级，不影响用户体验

---

## 数据指标面板 (Metrics Dashboard)

**访问路径**：`/admin/metrics`

**组件**：`app/admin/metrics/page.tsx`

**数据来源**：`GET /api/v1/metrics` → 后端从 `events` 表聚合计算

**展示指标**：

| 类别 | 指标 | 数据字段 |
|------|------|---------|
| 用户 | DAU（日活） | `dau` |
| 留存 | D1 留存率 | `d1_retention` |
| 留存 | D7 留存率 | `d7_retention` |
| 分析 | 总分析次数 | `total_analyses` |
| 分析 | 有帮助率 | `helpful_rate` |
| 分析 | 回复采纳率 | `reply_adoption_rate` |
| 分析 | 人均分析次数 | `analysis_count_per_user` |
| 分析 | 平均分析耗时 | `avg_analysis_duration_ms` |
| 分享 | 分享转化率 | `share_conversion_rate` |
| 分享 | 分享点击 | `share_clicked_count` |
| 分享 | 分享成功 | `share_succeeded_count` |

**本地开发访问**：`http://localhost:3000/admin/metrics`

---

## 部署配置

### 开发模式 (next dev)

```
next dev -H 0.0.0.0    → localhost:3000
```

API 请求通过 `next.config.ts` 的 `rewrites` 代理到 `localhost:8000`。

### 生产模式 (next start)

```
next build && next start -H 0.0.0.0 -p 3000
```

API 请求直连 `NEXT_PUBLIC_API_URL`（生产环境指向 Railway 部署地址）。

### Vercel 部署

`vercel.json` 指定构建命令、输出目录、生产环境变量。
