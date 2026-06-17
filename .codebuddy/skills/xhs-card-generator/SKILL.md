---
name: xhs-card-generator
description: 小红书图文卡片生成器。完整流程：读取纯文案（content_calendar.md）→ 根据文案内容到 BetweenLines 网站输入示例对话 → Playwright 截取分析结果 → 结合文案和截图生成 JSON 卡片数据 → 生成 HTML → Playwright 截图输出 PNG 卡片。触发词：卡片、card_data、build_cards、内容日历、小红书图片、截图生成、重新生成卡片、生成卡片。
---

# 小红书卡片生成器（完整流水线）

## 概述

从纯文案（`content_calendar.md`）到小红书风格图片卡片的**全自动流水线**：

```
纯文案 → 示例对话 → 网站输入分析 → 截图获取 → JSON数据 → HTML渲染 → PNG卡片
```

## 前置条件

- `xhs_docs/` 目录结构已就位
- `node` + `playwright` npm 包 + chromium 浏览器已安装
- Python 3 可用
- 网站 `http://localhost:3000` 前端 + `http://localhost:8000` 后端已启动

## 完整工作流程

### Step 0：确保服务运行

```bash
# 后端
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 前端
cd frontend && npx next dev -p 3000 &
```

### Step 1：生成示例对话截图

根据 `content_calendar.md` 中每天的文案内容，构造对应的示例对话，用 Playwright 打开网站输入对话、获取分析结果截图。

**脚本**：`scripts/capture_screenshots.py`

流程：
1. 读取 `content_calendar.md`，解析每天的主题和核心观点
2. 根据文案内容构造 1~3 组示例对话（体现该天的核心功能点）
3. 对每组对话：
   - `playwright_navigate` 打开 `http://localhost:3000`（viewport 1440×900 或更大）
   - 在聊天输入框填入对话内容（textbox 选择器：`textarea`）
   - 选择关系类型（如 `button:has-text('💕')`）
   - 点击分析按钮（`button:has-text('分析聊天')`）
   - 等待结果加载（`playwright_evaluate` 等待 25s）
   - **关键**：网站强制 390px 移动端宽度，截图会模糊。执行 `playwright_evaluate` 注入 CSS：
     ```js
     const h = document.documentElement;
     h.style.transform = 'scale(2.3)';
     h.style.transformOrigin = 'top left';
     h.style.width = '897px';
     ```
   - `playwright_screenshot` 全页截取，保存到 `xhs_docs/screenshots/`（命名：`dayXX_功能名.png`），输出分辨率 ~2063px 宽
4. 对于需要复盘截图的天（如 Day 10），先做第一次分析获取 `analysis_id`，再调用 `/api/v1/review` 截图

**截图清单**（按天）详见 `content_calendar.md` 中的 `[截图]` 标注。

### Step 2：生成卡片 JSON 数据

根据 `content_calendar.md` 的文案和 Step 1 生成的截图，在 `card_data/` 下创建 JSON 文件。

**生成规则**（详见 `references/card_spec.md`）：

每篇内容拆为 4~6 张卡片：

| 卡片序号 | id | class | 内容来源 |
|---------|-----|-------|---------|
| 第1张 | `cover` | `dark` | 标题 + emoji + 副标题 |
| 第2~4张 | `story1/2/3` | `white` | 文案拆段，每段 3~5 句 |
| 倒数第2张 | `screenshot` | `light-gray` | 说明文字 + 嵌入截图 |
| 最后1张 | `cta` | `dark` | 引导文案 + 链接 |

**内容拆分规则**：
- 封面标题 ≤12 字，从日历标题提取
- 每张正文卡 3~5 行，每行 ≤20 字
- 保持原文案的叙事节奏和口语风格
- 空行用 `""` 表示
- 截图卡文字说明截图内容，并嵌入对应截图路径
- CTA 卡引导用户访问

### Step 3：运行 `scripts/build_cards.py` 生成 PNG

```bash
cd xhs_docs && python3 build_cards.py
```

脚本自动完成：
1. 清理旧输出
2. 为每个 JSON 文件创建输出子文件夹
3. 每张卡片生成独立 HTML
4. 用 Playwright 截图（1080×1440, 2x retina）
5. 输出到 `output_cards/<天名>/<id>.png`

### Step 4：验证

- 所有卡片 2160×2880 分辨率
- 截图类卡片文字可见（不被截图挤出视口）
- 箭头方向与截图位置一致
- 截图引用的素材文件存在

## 常见问题

| 问题 | 原因 | 修复 |
|------|------|------|
| 截图没显示 | 路径不对 | 脚本自动补 `../../` |
| 文字被挤出 | 截图太大 | CSS `max-height:750px` |
| 箭头错误 | ↑但截图在下 | 改 ↓ |
| 对话示例不匹配文案 | 构造对话不准确 | 重新分析文案核心观点再构造 |
| 截图模糊 | 网站强制 390px 宽 | 截图前注入 `transform: scale(2.3)` 放大渲染，使输出达 2063px 宽 |
| 纯文字天不需要截图 | Day 5/8 等无 `[截图]` 标记 | 跳过 Step 1，直接从文案生成 JSON 数据 |
