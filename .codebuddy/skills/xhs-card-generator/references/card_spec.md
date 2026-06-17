# 卡片 JSON 数据格式规范

## 文件组织

```
xhs_docs/
├── content_calendar.md     # 纯文案（每篇：标题 + 正文 + 标签）
├── card_data/              # JSON 数据文件（由文案 + 截图生成）
├── screenshots/            # 产品截图（由 capture_screenshots.py 生成）
└── output_cards/           # 最终 PNG（按天分文件夹）
```

## 卡片字段

```json
{
  "id": "cover",           // 封面/正文/截图/CTA
  "class": "dark",         // dark | white | light-gray
  "emoji": "💬",           // （可选）大号 emoji
  "title": "标题",         // （可选）52px，\n 换行
  "subtitle": "副标题",   // （可选）28px
  "quote": "「引用」",    // （可选）左边红边框引用块
  "lines": [],            // （可选）正文行，"" = 空行
  "screenshot": "../screenshots/xxx.png",  // （可选）截图路径
  "cta": "引导文案",       // （可选）CTA 文字
  "cta_link": "链接文字",  // （可选）CTA 小字
  "dimmed": "Day 4"       // （可选）灰色小字
}
```

## 卡片类型模板

| 类型 | class | 必填 | 可选 |
|------|-------|------|------|
| 封面 | dark | id, emoji, title | subtitle, dimmed |
| 正文 | white | id, lines | quote |
| 截图展示 | light-gray | id, lines, screenshot | - |
| CTA | dark | id, cta | emoji, cta_link |

## 内容规范

- 封面标题 ≤12 字
- 正文每卡 3~5 行，行 ≤20 字
- `<highlight>文本</highlight>` 标记红色高亮
- 用户引用用「」中文引号
- 空行用 `""`

## 布局参数

- 卡片 1080×1440px，padding 80px
- 截图 `max-height:750px`，`object-fit:contain`
- 箭头方向与截图位置一致
