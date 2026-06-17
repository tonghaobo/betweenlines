---
name: auto-verify
description: 每次修改代码后自动运行测试直到通过。后端运行 --no-ai 校验，前端运行 build 检查。触发词：verify、test、check、build、run tests、regression、commit、提交、验证、测试、检查、auto test。
---

# Auto-Verify

## 概述

每次修改代码后，自动运行对应的 Level 1 测试（零 AI Token），失败则修复后重试，直到全部通过才能认为任务完成。

## 强制规则

**代码修改后，必须先跑测试，测试通过后才能停下。不允许在测试未通过时声称任务完成。**

## 变更检测与测试选择

根据 `git diff --name-only` 或刚刚修改的文件，判断需要运行哪些测试：

| 变更范围 | 运行命令 | 耗时 | Token |
|---------|---------|------|-------|
| `backend/**/*.py`（不含 tests/） | `python tests/test_comprehensive.py --no-ai` | <5s | 0 |
| `frontend/src/**/*.{ts,tsx}` | `npx next build --no-lint 2>&1 \| tail -5` | ~30s | 0 |
| 后端 + 前端同时改动 | 先后端再前端 | ~35s | 0 |
| 仅文档/配置/测试文件 | 跳过（告知用户原因） | — | — |

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

### Step 2：运行测试

```bash
# 后端
cd backend && python tests/test_comprehensive.py --no-ai

# 前端
cd frontend && npx next build --no-lint 2>&1 | tail -5
```

### Step 3：判断结果

**后端通过**：输出 `6/6 校验通过` 或 `所有测试通过`

**前端通过**：输出中不含 `error` 或 `Error`，且 exit code 为 0

### Step 4：失败处理（迭代修复）

```
1. 分析失败原因（读报错信息）
2. 修复代码
3. 重新运行测试
4. 如果仍然失败 → 回到步骤 1
5. 最多 5 轮迭代
6. 5 轮后仍未通过 → 报告用户，请求指导
```

### Step 5：报告结果

测试通过后，以简洁格式报告：

```
✓ 后端: 6/6 校验通过
✓ 前端: build 通过
```

## 什么不自动运行

| 禁止自动运行 | 原因 |
|------------|------|
| `test_comprehensive.py`（全量 AI 场景） | 消耗 45k-120k Token |
| `test_comprehensive.py --test=X,Y` | 消耗 3k-8k/场景 Token |
| `test_api.py` | 全量 AI 调用 |
| `test_prompt.py` | 直接调用豆包 API |

**如果判断 AI 测试有必要**（如改了 System Prompt），先向用户报告 Token 消耗预估，获得同意后再运行。

## 何时跳过

以下情况可跳过验证，但需告知用户原因：

- 仅修改 `*.md`、`.gitignore`、`README` 等非代码文件
- 仅修改测试文件（`tests/**`）
- 用户明确说"不用测试"或"skip tests"

## 与 TDD 的关系

- **TDD skill**：在写实现代码之前先写测试（RED → GREEN → REFACTOR）
- **auto-verify skill**：在修改代码之后验证已有测试（REGRESSION CHECK）
- 两者互补，不重复
