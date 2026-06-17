# 功能路线图

---

## 已完成

| 功能 | 说明 |
|------|------|
| 氛围分析 + 回复建议 + 风险提醒 + 节奏建议 | 核心分析能力 |
| 截图 OCR | 支持上传截图自动提取文字 |
| 反馈收集 + 24h 回访 + 采纳追踪 | 反馈闭环基础 |
| 分享卡片 + 中英双语 | 增长和国际化 |
| 聊天拐点检测 | 自动定位对话氛围变化的转折点 |
| 对话走势预测 | 预测每种回复方式的可能走向 |
| 回复后复盘 | 上传后续聊天，对比分析建议效果 |
| 自动标签系统 | 对话智能分类，精准匹配参考案例 |
| 错误案例 Dashboard | 基于差评数据的质量监控面板 |

---

## 计划中

| 功能 | 说明 |
|------|------|
| Prompt 优化闭环 | 基于差评数据持续精调 AI 分析质量（F4.2 Prompt Revision SOP） |

---

## 远期

| 功能 | 说明 |
|------|------|
| 相似案例推荐 | 找到和你的情况相似的、结果成功的案例作为参考 |
| 长期关系曲线 | 多次复盘数据汇总，可视化关系走势变化 |

---

## 反馈系统 Phase 状态

| Phase | 模块 | 任务 | 状态 |
|-------|------|------|------|
| 1 | Feedback Collection | F1.1 分析后反馈组件 | ✅ 已实现 |
| 1 | Feedback Collection | F1.2 负反馈原因采集 | ✅ 已实现 |
| 1 | Feedback Collection | F1.3 正反馈原因采集 | ✅ 已实现 |
| 1 | Feedback Collection | F1.4 Feedback API | ✅ 已实现 |
| 1 | Feedback Collection | F1.5 正面反馈自动收集优质案例 | ✅ 已实现 |
| 2 | Outcome Tracking | F2.1 建议采用率采集 | ✅ 已实现 |
| 2 | Outcome Tracking | F2.2 Follow-up 回访系统 | ✅ 已实现 |
| 2 | Outcome Tracking | F2.3 Outcome API | ✅ 已实现 |
| 3 | Data Labeling | F3.1 自动标签生成 | ✅ 已实现 |
| 3 | Data Labeling | F3.2 标签数据库 | ✅ 已实现 |
| 4 | Prompt Optimization | F4.1 错误案例 Dashboard | ✅ 已实现 |
| 4 | Prompt Optimization | F4.2 Prompt Revision SOP | ❌ 待实现 |
| 5 | Similar Case Retrieval | F5 相似案例推荐 | 🔒 设计预留 |

---

## 核心指标

| 阶段 | 指标 | 目标 |
|------|------|------|
| Phase 1 | helpful_rate | > 50% |
| Phase 2 | reply_adoption_rate | > 30% |
| Phase 3 | positive_outcome_rate | > 40% |
| 长期 | return_rate | > 25% |
