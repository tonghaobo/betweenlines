---
name: auto-verify
description: 每次修改代码后自动运行测试直到通过。后端运行 --no-ai 校验，前端运行 build 检查。触发词：verify、test、check、build、run tests、regression、commit、提交、验证、测试、检查、auto test。
---

# Auto-Verify

## 概述

每次修改代码后，自动运行对应的 Level 1 测试（零 AI Token）。Level 1 通过后，自动运行 Level 1.5 轻量功能验证（2 轮 AI 对话分析，≤6k Token，使用独立测试模型 `doubao-1-5-lite-32k-250115`，不在生产 TEXT_MODELS 中）。失败则修复后重试 Level 1，直到全部通过才能认为任务完成。

## 强制规则

**代码修改后，必须先跑测试，Level 1 全部通过后才能停下。Level 1.5 仅观察不阻塞（AI 输出有随机性）。不允许在 Level 1 未通过时声称任务完成。**

## 变更检测与测试选择

根据 `git diff --name-only` 或刚刚修改的文件，判断需要运行哪些测试：

| 变更范围 | Level 1 命令 | 耗时 | Level 1.5 功能验证 |
|---------|-------------|------|-------------------|
| `backend/**/*.py`（不含 tests/） | `python tests/test_comprehensive.py --no-ai` | <5s | ✅ 自动运行 |
| `frontend/src/**/*.{ts,tsx}` | `npx next build --no-lint 2>&1 \| tail -5` | ~30s | ❌ 跳过 |
| 后端 + 前端同时改动 | 先后端再前端 | ~35s | ✅ 自动运行 |
| 仅文档/配置/测试文件 | 跳过（告知用户原因） | — | ❌ 跳过 |

## Token 消耗红线（最高优先级）

> **⚠️ 这是不可逾越的硬规则，违反则自动停止。**

| 规则 | 说明 |
|------|------|
| 🔴 **Level 1 必须零 Token** | 任何代码修改后，首先运行 `--no-ai` 校验 + `next build`，此阶段 Token 消耗必须为 0 |
| 🟢 **Level 1.5 轻量功能验证（自动）** | Level 1 全部通过后，自动运行 2 轮 AI 对话分析（≤6k Token，用 `doubao-1-5-lite-32k` 独立测试模型，不在生产列表中），验证核心分析链路是否正常 |
| 🔴 **禁止 AI 测试重试** | AI 输出有随机性，重试无意义且浪费 Token。Level 1.5 最多执行 **1 次**，不重试 |
| 🔴 **全量测试 = 用户手动触发** | 全量 15 个 AI 场景测试**绝不自动运行、绝不主动建议、绝不询问用户**。只有用户明确说"全量测试""跑 AI 场景""加上 Phase 2"等关键词时才触发 |
| 🟡 **重试上限 3 轮** | 重试只适用于 Level 1（零 Token 校验），最多 3 轮 |

### 执行前强制自检

每次运行测试前，Agent 必须在内部确认：

```
□ Level 1 校验：我要跑的命令是否包含 --no-ai？
  如果不是 → 立即停止。除非用户在本次对话中明确说了"全量测试"。
□ Level 1 是否全部通过？
  如果否 → 继续修复，不进入 Level 1.5。
□ Level 1.5 功能验证：Level 1 全部通过后，自动跑 2 轮 AI 场景。
  ① 先重启后端，带上 TEST_OVERRIDE_MODEL=doubao-1-5-lite-32k-250115
  ② 执行：python tests/test_comprehensive.py --test=积极互动,解题模式_典型
  ③ 完成后重启后端（不带 TEST_OVERRIDE_MODEL），恢复正常配置
  Token 预算：≤6k（2 场景 × ~3k），执行 1 次不重试。
□ 用户是否明确要求了全量测试？
  如果否 → 只做 Level 1 + Level 1.5，不做全量 15 场景。
□ 我是不是在重试 Level 1？
  如果是 → 确认仍然在用 --no-ai，没有切换到 AI 模式。
```

## 工作流程

### Step 1：确保后端运行

运行后端测试前，先确认 `http://localhost:8000/health` 可达：

```bash
curl -s http://localhost:8000/health || echo "BACKEND_DOWN"
```

如果后端未运行，启动它：

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

等待最多 10 秒，每 2 秒检查一次健康状态。超时则报告用户。

### Step 2：运行测试（仅 Level 1，零 Token）

```bash
# 后端：仅校验，不调 AI
cd backend && python tests/test_comprehensive.py --no-ai

# 前端：仅 build 检查
cd frontend && npx next build --no-lint 2>&1 | tail -5
```

### Step 3：判断结果

**后端通过**：所有校验项通过，输出 `校验通过: N/N`

**前端通过**：输出中不含 `error` 或 `Error`，且 exit code 为 0

### Step 4：失败处理（仅 Phase 1 重试，零 Token）

```
1. 分析失败原因（读报错信息）
2. 判断：是代码 bug 还是校验场景缺失？
   - 代码 bug → 修复代码
   - 校验场景缺失 → 先加场景到测试文件（见 Step 4.5），再修复代码
3. 重新运行 --no-ai 测试（必须带 --no-ai）
4. 如果仍然失败 → 回到步骤 1
5. 最多 3 轮迭代
6. 3 轮后仍未通过 → 报告用户，请求指导
```

**重试时禁止行为**：
- ❌ Level 1 失败时，不得切换到 AI 测试来"验证修复"
- ❌ 不得运行 `test_api.py` 或 `test_prompt.py` 来"验证修复"
- ❌ 不得因为 Level 1 失败而跳过直接进 Level 1.5

### Step 4.5：错误模式学习（校验场景自增长）

> **核心理念**：每次遇到新的错误模式，将其固化为永久的零 Token 校验场景，防止同类问题再次出现。

**何时添加新校验场景**：

| 判定条件 | 示例 |
|----------|------|
| 代码修改引入的 bug 未被现有校验捕获 | 改了验证逻辑，新边界条件没测到 |
| 生产/开发中发现的新错误模式 | 某个 API 返回了非预期状态码 |
| 发现现有校验覆盖不到的输入组合 | 带特殊字符的输入、并发请求等 |
| 后端新增了 API 端点但校验未覆盖 | 新增 `/api/v1/xxx`，没加对应的 200/400 校验 |

**添加方式**：

在 `backend/tests/test_comprehensive.py` 的 `VALIDATION_CASES` 列表中追加新条目：

```python
# 示例：发现 Unicode 特殊字符导致后端崩溃
{"name": "特殊Unicode校验(200)", "method": "POST", "path": "/api/v1/analyze",
 "body": {"chat_content": "我: 你好\u200b她: 嗯", "anonymous_user_id": "test_val"},
 "expect_status": 200},
```

**添加后必须**：
1. 重新运行 `--no-ai` 确认新场景通过
2. 在 Step 5 报告中注明新增了哪些校验场景

### Step 5：报告 Level 1 结果

Level 1 全部通过后，先报告：

```
✓ 后端: 校验通过: N/N (0 Token)
✓ 前端: build 通过
```

如有新增校验场景：
```
📋 新增校验场景: "特殊Unicode校验(200)"
   当前校验总数: N 项
```

### Step 5.5：轻量功能验证（Level 1.5，自动执行）

> **触发条件**：Level 1（后端 + 前端）全部通过后自动执行。不询问用户，直接跑。

**目的**：用最廉价模型快速验证核心 AI 分析链路是否正常，观察基本指标。

**测试模型**：`doubao-1-5-lite-32k-250115`（独立测试模型，不在生产 TEXT_MODELS 中，配额完全隔离）

**预设场景**（2 轮，覆盖正常分析 + 深层信号）：

| 场景 | 覆盖维度 | 预估 Token |
|------|---------|-----------|
| `积极互动` | 正常分析流程 · 状态分类 · 回复质量 | ~3k |
| `解题模式_典型` | 深层信号检测 · 原文引用 · 反套话 | ~3k |

**执行流程**：

```bash
# ① 找到并 kill 当前后端进程
pkill -f "uvicorn app.main" 2>/dev/null; sleep 1

# ② 用测试模型启动后端
cd backend && source .venv/bin/activate && TEST_OVERRIDE_MODEL=doubao-1-5-lite-32k-250115 uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# ③ 等待后端就绪（最多 10s，每 2s 检查 /health）
# health 可达后执行：
cd backend && python tests/test_comprehensive.py --test=积极互动,解题模式_典型

# ④ 恢复正式配置（kill 测试后端，重新启动正式后端）
pkill -f "uvicorn app.main" 2>/dev/null; sleep 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

**Token 预算**：≤6k Token（2 场景 × ~3k）

**观察指标**（重点关注）：

| 指标 | 正常范围 | 异常判定 |
|------|---------|---------|
| 分析耗时 | < 15s/场景（mini 模型快） | > 30s 需关注 |
| HTTP 状态码 | 全部 200 | 任何非 200 需排查 |
| 分析内容长度 | 30~200 字 | 空内容或 >200 字异常 |
| 状态分类 | 与实际场景匹配或相邻 | 偏差 ≥2 级异常 |
| 回复质量 mark | reply_ok = ✅ | 出现泛化兜底回复异常 |
| 深层信号 | 解题模式检测到"方案/共情/建议"关键词 | 全部遗漏异常 |

**结果报告格式**：

```
🔍 Level 1.5 轻量功能验证 (模型: doubao-1-5-lite-32k, ≤6k Token)

  ✅ 积极互动       — 耗时Xs, 分析XXX字, 状态=积极互动, 回复✅ 信号✅
  ✅ 解题模式_典型   — 耗时Xs, 分析XXX字, 状态=偏冷淡, 引用✅ 信号✅

  📊 健康评估: 2/2 通过
  ⏱️ 平均耗时: Xs | 📏 平均分析长度: XXX字
  ✅ 核心分析链路正常
  ↩️  已恢复正式模型配置
```

**异常处理**：

- 场景失败不重试（AI 输出有随机性）
- 如果 2/2 失败 → 报告用户，可能是模型/配置/网络问题
- 如果 1/2 失败 → 标注异常但不阻塞，告知用户关注
- **禁止行为**：不得因 Level 1.5 失败而重试、不得误用正式模型重跑

**⚠️ 关键规则：测试完成后必须恢复正式模型**

Level 1.5 完成后，Agent **必须**执行 Step ④（重启后端不带 `TEST_OVERRIDE_MODEL`），否则后续正常请求都会走到廉价模型。

**自动裁剪**（Agent 根据改动范围决策）：

| 本次改动范围 | Level 1.5 执行策略 |
|------------|-------------------|
| 仅前端改动（UI/组件/CSS） | **跳过**（前端改动不影响 AI 分析链路） |
| 仅后端路由/中间件/校验改动 | 只跑 `积极互动` 1 个场景（验证链路通畅） |
| 后端 AI 服务/提示词/模型配置改动 | 跑全部 2 个默认场景 |
| 仅文档/配置/测试文件 | 整个 auto-verify 跳过 |

### Step 6：全量 AI 级别验证（用户手动触发）

**Agent 不得主动提议、询问、或暗示需要全量验证。**

只有当用户在本次对话中明确说"全量测试""跑 AI 场景""加上 Phase 2""跑一下模型响应"等关键词时，才执行全量 AI 测试：

```bash
# 全量（15 场景）
cd backend && python tests/test_comprehensive.py

# 指定场景
cd backend && python tests/test_comprehensive.py --test=场景名1,场景名2
```

运行前需报告预估 Token 消耗。

## 什么不自动运行

| 禁止自动运行 | 原因 | Token 消耗 |
|------------|------|-----------|
| `test_comprehensive.py`（全量 15 场景） | 场景多，Token 消耗大 | 45k-120k Token |
| `test_api.py` | 全量 AI 调用 | 不确定，取决于测试范围 |
| `test_prompt.py` | 直接调用豆包 API | 不确定 |
| `test_comprehensive.py` 不带 `--no-ai` 的重试 | AI 输出有随机性，重试浪费 Token | 每次 ~100k Token |

## 自动运行范围

| 自动运行 | 条件 | Token 消耗 |
|---------|------|-----------|
| `test_comprehensive.py --no-ai` | 后端代码改动 | 0 Token |
| `next build --no-lint` | 前端代码改动 | 0 Token |
| `test_comprehensive.py --test=预设2场景` | Level 1 全部通过 + 后端改动 | ≤6k Token（1 次不重试，使用 `doubao-1-5-lite-32k` 独立测试模型） |

**Agent 不得主动建议、询问、或暗示用户运行全量 15 场景 AI 测试。**

## 零 Token 校验的覆盖范围

校验场景定义在 `backend/tests/test_comprehensive.py` 的 `VALIDATION_CASES` 列表中，**可动态增长**。

当前覆盖：

| 校验项 | 方法 | 说明 |
|--------|------|------|
| 空输入 / 超短输入 | POST `/api/v1/analyze` | <10 字符 |
| 超长输入 | POST `/api/v1/analyze` | >5000 字符 |
| 违规内容拦截 | POST `/api/v1/analyze` | PUA 等敏感词 |
| 纯空白输入 | POST `/api/v1/analyze` | 仅含空白字符 |
| 健康检查 | GET `/health` | 200 OK |
| 统计接口 | GET `/api/v1/stats` | 200 OK |

随着错误模式积累，`VALIDATION_CASES` 列表会持续增长，逐步覆盖更多边界条件。所有新增场景均为零 Token。

## 何时跳过

以下情况可跳过验证，但需告知用户原因：

- 仅修改 `*.md`、`.gitignore`、`README` 等非代码文件
- 仅修改测试文件（`tests/**`）
- 用户明确说"不用测试"或"skip tests"

## 与 TDD 的关系

- **TDD skill**：在写实现代码之前先写测试（RED → GREEN → REFACTOR）
- **auto-verify skill**：在修改代码之后验证已有测试（REGRESSION CHECK）
- 两者互补，不重复
