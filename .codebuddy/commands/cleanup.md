---
description: 扫描并清除项目中的废弃/多余文件
argument-hint: "[--dry-run] [--all]"
---

# Cleanup — 清除废弃多余文件

## 目标

扫描项目中不再需要的文件（已废弃规则、根目录散落文档、未跟踪临时文件等），清理并保持仓库整洁。

## 扫描规则

按以下优先级逐项扫描，每项标注来源和废弃原因：

### 1. 已废弃的规则文件
```bash
# 查找 enabled: false 的 .mdc 规则文件
grep -rl "enabled: false" .codebuddy/rules/ 2>/dev/null
```

### 2. 根目录散落文档（应在 docs/ 或 plans/ 下）
```bash
# 根目录下不在 docs/、plans/、.codebuddy/ 的 .md 文件
ls *.md 2>/dev/null | grep -v README.md | grep -v CODEBUDDY.md
```

### 3. 根目录其他散落文件（.txt / .plan / .backup 等）
```bash
ls *.txt *.plan *.backup *.draft 2>/dev/null
```

### 4. 未跟踪文件（git status --porcelain 中 ?? 状态）
```bash
git status --porcelain | grep '^??' | awk '{print $2}'
```

### 5. 空目录
```bash
find . -type d -empty -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./.venv/*" -not -path "./.next/*" 2>/dev/null
```

## 流程

1. **扫描**：执行上述 5 条规则，汇总待清理文件列表
2. **展示**：以表格形式列出，包含：文件路径、大小、废弃原因
3. **确认**：
   - `--all`：跳过确认，直接清理所有
   - `--dry-run`：仅列出，不执行删除
   - 默认：逐项询问用户确认
4. **执行**：`git rm` 已跟踪文件 / `rm` 未跟踪文件
5. **报告**：清理数量、释放空间

## 安全约束

- 不删除 `README.md`、`CODEBUDDY.md`、`.gitignore`、`.env`
- 不删除 `node_modules/`、`.venv/`、`.next/` 下的文件
- 不删除 `docs/`、`plans/` 下的文件
- 不删除 git tracked 且 enabled 的规则文件
- 删除前必须展示清单并获得用户确认（`--all` 除外）

## 执行

如果用户传递了参数，解析后按上述流程执行。默认交互模式，先扫描展示，再逐项确认删除。
