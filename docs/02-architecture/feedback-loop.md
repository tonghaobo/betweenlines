# 用户反馈闭环系统

> 版本：V1 → V3  
> 目标：通过真实用户反馈，逐步提高聊天分析质量与回复建议效果。

---

## 核心原则

1. 前期不训练模型
2. 优先建立反馈飞轮
3. 收集 outcome（结果）而不是主观感受
4. 永远从真实用户行为学习
5. 所有功能必须服务于：**更准 + 更留存**

---

## 整体架构

目标飞轮：

```text
用户上传聊天 → AI 分析 → 用户选择回复建议 → 用户发送消息
→ 第二天追踪结果 → 收集 outcome → 优化 prompt → 提升准确率 → 留存提高
```

系统拆分为 5 个模块：

1. Feedback Collection（反馈采集）
2. Outcome Tracking（结果追踪）
3. Data Labeling（标签化）
4. Prompt Optimization（Prompt 优化）
5. Similar Case Retrieval（相似案例检索）

---

## 实现状态总览

| Phase | 模块 | 任务 | 状态 |
|-------|------|------|------|
| 1 | Feedback Collection | F1.1 分析后反馈组件 | ✅ 已实现 |
| 1 | Feedback Collection | F1.2 负反馈原因采集 | ✅ 已实现 |
| 1 | Feedback Collection | F1.3 正反馈原因采集 | ✅ 已实现 |
| 1 | Feedback Collection | F1.4 Feedback API | ✅ 已实现 |
| 1 | Feedback Collection | F1.5 正面反馈自动收集优质案例（Few-Shot 学习） | ✅ 已实现 |
| 2 | Outcome Tracking | F2.1 建议采用率采集 | ✅ 已实现 |
| 2 | Outcome Tracking | F2.2 Follow-up 回访系统 | ✅ 已实现 |
| 2 | Outcome Tracking | F2.3 Outcome API | ✅ 已实现 |
| 3 | Data Labeling | F3.1 自动标签生成 | ❌ 待实现 |
| 3 | Data Labeling | F3.2 标签数据库 | ❌ 待实现 |
| 4 | Prompt Optimization | F4.1 错误案例 Dashboard | ❌ 待实现 |
| 4 | Prompt Optimization | F4.2 Prompt Revision SOP | ❌ 待实现 |
| 5 | Similar Case Retrieval | F5 相似案例推荐 | ❌ V3 阶段 |

---

## Phase 1：基础反馈系统（已实现）

### F1.1 分析后反馈组件

- 组件：`FeedbackSection.tsx`
- 位置：结果页底部
- 功能：显示 👍/👎 按钮，点击后弹出二级原因选择

### F1.2 负反馈原因采集

- 触发：点击 👎 时
- 多选选项：不够准确 / 回复太尴尬 / 太泛泛 / 不适合我的情况 / 看不懂 / 其他
- 支持文本输入
- 数据库字段：`reason`, `comment`

### F1.3 正反馈原因采集

- 触发：点击 👍 时
- 问题：哪部分最有帮助？
- 多选选项：态度分析 / 回复建议 / 节奏建议 / 风险提醒 / 很真实
- 支持文本输入

### F1.4 Feedback API

- 端点：`POST /api/v1/feedback`
- 请求体：`{ analysis_id, helpful, reason: string[], comment: string }`
- 数据表：`feedback` (id, analysis_id, helpful, reason, comment, created_at)

### F1.5 正面反馈自动收集优质案例（Few-Shot 学习）🆕

当用户点击 👍 时，自动将当前分析的统计特征和 AI 输出保存为优质案例：

**数据流**：
```
分析完成 → _recent_analyses[user_id] = {features, analysis_json}（仅内存）
用户点 👍 → save_good_case(features, relationship, analysis_json)
下次分析 → get_good_cases() → 注入到 User Prompt 中
```

**隐私设计**：仅存储提取后的统计特征（消息数、均长、问句比、显著模式），**不存储聊天原文**。

**Few-Shot 注入层次**：
1. **静态示例**（始终嵌入）：2 个中英文对比示例，提供基础质量锚定
2. **动态示例**（DB 加载）：按关系类型匹配的优质案例，最多 2 条

**自动管理**：
- 去重：SHA-256 特征 hash，相同模式不重复存储
- 容量：上限 100 条，超出自动删除最旧记录
- 非阻塞：存储失败不影响主流程

**数据表**：`good_cases`（仅特征字段 + analysis_json）

---

## Phase 2：Outcome Tracking（已实现）

### F2.1 建议采用率采集

- 组件：`ReplyAdoptionCard.tsx`
- 问题：你发送了建议回复吗？
- 单选：发了 / 没发 / 改了一下再发

### F2.2 Follow-up 回访系统

- 组件：`FollowUpReminder.tsx`
- 技术：localStorage 保存分析时间，24 小时后在首页弹出浮层提醒
- 选项：回复更积极 / 差不多 / 更冷淡 / 没回复 / 不想说

### F2.3 Outcome API

- 端点：`POST /api/v1/outcome`
- 请求体：`{ analysis_id, reply_used, outcome }`
- 数据表：`outcome` (id, analysis_id, reply_used, outcome, created_at)

---

## Phase 3：标签系统（待实现）

### F3.1 自动标签生成

分析结果新增标签：

- `conversation_stage`：初识 / 熟悉 / 暧昧 / 拉扯 / 冷淡
- `other_style`：热情型 / 礼貌型 / 高冷型 / 慢热型
- `user_issue`：查户口 / 太急 / 输出太多 / 幽默不足

### F3.2 标签数据库

新增表 `analysis_tags`：analysis_id, conversation_stage, other_style, user_issue, outcome

---

## Phase 4：Prompt 优化闭环（待实现）

### F4.1 错误案例 Dashboard

- 统计最多差评原因
- 使用 Recharts 展示

### F4.2 Prompt Revision SOP

- 每周导出差评案例，分析原因，每次只改一个变量

---

## Phase 5：相似案例推荐（V3 阶段）

- 逻辑：用户聊天 → embedding → 找相似聊天 → 找成功案例 → 给建议
- 数据表：`successful_cases` (chat_embedding, conversation_stage, reply_style, reply_text, outcome)

---

## 核心指标

| 阶段 | 指标 | 目标 |
|------|------|------|
| Phase 1 | helpful_rate | > 50% |
| Phase 2 | reply_adoption_rate | > 30% |
| Phase 3 | positive_outcome_rate | > 40% |
| 长期 | return_rate | > 25% |

---

## 绝对禁止

1. 一开始训练模型
2. 一开始做向量数据库
3. 一开始做 RAG
4. 复杂推荐系统
