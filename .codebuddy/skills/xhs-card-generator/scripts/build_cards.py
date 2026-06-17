"""卡片生成器：读取 card_data/*.json → 每张卡片独立 HTML → Playwright 截图 → 1080x1440 PNG。"""

import json, os, subprocess, glob, shutil

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SELF_DIR, "card_data")
OUTPUT_DIR = os.path.join(SELF_DIR, "output_cards")
TEMP_HTML_DIR = os.path.join(OUTPUT_DIR, "_temp_html")

W, H = 1080, 1440
LOGO = "betweenlines"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1440px;overflow:hidden}
body{font-family:"PingFang SC","Noto Sans SC","Helvetica Neue",sans-serif}
.card{width:1080px;height:1440px;position:relative;display:flex;flex-direction:column;justify-content:center;padding:80px}
.card.dark{background:linear-gradient(160deg,#0f0f23 0%,#1a1a2e 100%);color:#fff}
.card.white{background:#fff;color:#1a1a1a}
.card.light-gray{background:#f8f9fb;color:#1a1a1a}
.emoji-lg{font-size:72px;margin-bottom:28px}
.title{font-size:52px;font-weight:800;line-height:1.25;letter-spacing:-0.5px}
.subtitle{font-size:28px;font-weight:400;color:rgba(255,255,255,0.55);margin-top:16px}
.body{font-size:34px;font-weight:400;line-height:1.7;letter-spacing:-0.2px}
.quote{font-size:36px;font-weight:500;line-height:1.6;color:#333;border-left:5px solid #ff6b6b;padding-left:24px;margin-top:20px}
.screenshot-box{background:#fff;border-radius:24px;padding:16px;box-shadow:0 8px 32px rgba(0,0,0,0.12);margin:24px 0;display:flex;justify-content:center}
.screenshot-box img{max-width:100%;max-height:750px;border-radius:12px;display:block;object-fit:contain}
.cta-text{font-size:34px;font-weight:600;line-height:1.6}
.cta-link{font-size:26px;color:rgba(255,255,255,0.45);margin-top:12px}
.dimmed{color:rgba(255,255,255,0.3);font-size:22px;margin-top:24px}
.logo-corner{position:absolute;bottom:48px;right:64px;font-size:22px;font-weight:600;letter-spacing:1px}
.logo-corner-dark{color:rgba(255,255,255,0.25)}
.logo-corner-light{color:#ccc}
.line{margin-top:4px}
.section{margin-top:20px}
"""


def card_html(card: dict) -> str:
    cls = card.get("class", "dark")
    html = f'<div class="card {cls}">'
    
    if card.get("emoji"):
        html += f'<div class="emoji-lg">{card["emoji"]}</div>'
    
    if card.get("title"):
        html += f'<div class="title">{card["title"]}</div>'
    
    if card.get("subtitle"):
        html += f'<div class="subtitle">{card["subtitle"]}</div>'
    
    if card.get("quote"):
        html += f'<div class="quote">{card["quote"]}</div>'
    
    lines = card.get("lines", [])
    if lines:
        html += '<div class="section">'
        for line in lines:
            if line == "":
                html += '<div style="height:12px"></div>'
            else:
                text = line.replace("<highlight>", '<strong style="color:#ff6b6b;font-weight:700">')
                text = text.replace("</highlight>", '</strong>')
                html += f'<div class="body line">{text}</div>'
        html += '</div>'
    
    if card.get("screenshot"):
        html += f'<div class="screenshot-box"><img src="{card["screenshot"]}" alt="screenshot"></div>'
    
    if card.get("cta"):
        html += f'<div style="margin-top:24px"><div class="cta-text">{card["cta"]}</div></div>'
        if card.get("cta_link"):
            html += f'<div class="cta-link">{card["cta_link"]}</div>'
    
    if card.get("dimmed"):
        html += f'<div class="dimmed">{card["dimmed"]}</div>'
    
    logo_cls = "logo-corner logo-corner-dark" if cls == "dark" else "logo-corner logo-corner-light"
    html += f'<div class="{logo_cls}">{LOGO}</div>'
    html += '</div>'
    return html


def generate_single_card_html(card: dict, output_path: str):
    """生成单张卡片的完整独立 HTML 文件。

    HTML 生成在 output_cards/_temp_html/ 下，需修正截图相对路径
    从 JSON 里的 ../screenshots/ → ../../screenshots/
    """
    # 深拷贝 card，避免修改原始数据
    card_fixed = dict(card)
    if card_fixed.get("screenshot") and card_fixed["screenshot"].startswith("../"):
        # 从 temp_html 目录到 screenshots 目录需要 ../../
        card_fixed["screenshot"] = "../.." + card_fixed["screenshot"][2:]

    html = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
    html += card_html(card_fixed)
    html += '</body></html>'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def screenshot_card(html_path: str, png_path: str):
    """使用 Playwright MCP 风格的 npx playwright screenshot 命令截图。"""
    abs_html = os.path.abspath(html_path)
    abs_png = os.path.abspath(png_path)
    
    # playwright screenshot 默认保存到当前目录，需要 cd 到输出目录
    png_name = os.path.basename(png_path)
    output_dir = os.path.dirname(abs_png)
    
    cmd = f'cd "{output_dir}" && npx playwright screenshot "file://{abs_html}" "{png_name}" --viewport-size=1080,1440 2>&1'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    
    if result.returncode != 0:
        print(f"  ❌ 截图失败: {result.stderr.strip()}")
        return False
    return True


# ═══════════════════════════════════════════════════════════════
# 使用 Node.js 批处理截图（更可靠）
# ═══════════════════════════════════════════════════════════════

def generate_screenshot_script(html_files: list[tuple[str, str]]):
    """生成 Node.js 批处理截图脚本，一次性处理所有卡片。"""
    script_path = os.path.join(SELF_DIR, "_screenshot_batch.mjs")
    
    entries = []
    for html_path, png_path in html_files:
        entries.append({
            "html": os.path.abspath(html_path),
            "png": os.path.abspath(png_path),
        })
    
    script = f"""// 批量截图脚本：每个 HTML → 1080×1440 PNG
import {{ chromium }} from 'playwright';
import {{ fileURLToPath }} from 'url';
import {{ dirname }} from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const cards = {json.dumps(entries, indent=2, ensure_ascii=False)};

(async () => {{
    const browser = await chromium.launch();
    
    for (const card of cards) {{
        const context = await browser.newContext({{
            viewport: {{ width: 1080, height: 1440 }},
            deviceScaleFactor: 2,
        }});
        const page = await context.newPage();
        
        try {{
            await page.goto('file://' + card.html, {{ waitUntil: 'networkidle' }});
            await page.screenshot({{
                path: card.png,
                fullPage: false,
            }});
            console.log('✅ ' + card.png.split('/').pop());
        }} catch (e) {{
            console.error('❌ ' + card.png.split('/').pop() + ': ' + e.message);
        }} finally {{
            await context.close();
        }}
    }}
    
    await browser.close();
    console.log('\\\\n🎉 全部完成！');
}})();
"""
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    
    return script_path


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 清理旧的输出
    shutil.rmtree(TEMP_HTML_DIR, ignore_errors=True)
    os.makedirs(TEMP_HTML_DIR, exist_ok=True)

    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    print(f"📂 发现 {len(json_files)} 个数据文件\n")

    all_html_png_pairs = []
    day_folders = []

    for jf in json_files:
        name = os.path.splitext(os.path.basename(jf))[0]
        with open(jf, "r", encoding="utf-8") as f:
            cards = json.load(f)

        # 为每天创建子文件夹
        day_dir = os.path.join(OUTPUT_DIR, name)
        # 清理旧文件夹后重建
        shutil.rmtree(day_dir, ignore_errors=True)
        os.makedirs(day_dir, exist_ok=True)
        day_folders.append(name)

        print(f"📝 {name}/ ({len(cards)} 张卡片)")

        for i, card in enumerate(cards):
            card_id = card.get("id", f"card{i+1}")
            html_filename = f"{name}_{card_id}.html"
            # PNG 只保留卡片 ID，因为已经在对应的天文件夹里了
            png_filename = f"{card_id}.png"

            html_path = os.path.join(TEMP_HTML_DIR, html_filename)
            png_path = os.path.join(day_dir, png_filename)

            generate_single_card_html(card, html_path)
            all_html_png_pairs.append((html_path, png_path))
            print(f"  → {png_filename}")

    # 清理 output_cards 根下的旧扁平文件
    for old_png in glob.glob(os.path.join(OUTPUT_DIR, "*.png")):
        os.remove(old_png)
    for old_html in glob.glob(os.path.join(OUTPUT_DIR, "*.html")):
        os.remove(old_html)

    print(f"\n📸 开始截图（共 {len(all_html_png_pairs)} 张）...\n")

    # 生成 Node.js 批处理脚本
    script_path = generate_screenshot_script(all_html_png_pairs)

    # 运行截图
    result = subprocess.run(
        ["node", script_path],
        cwd=SELF_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )

    print(result.stdout)
    if result.stderr and "✅" not in result.stderr:
        print("STDERR:", result.stderr)

    # 清理临时文件
    shutil.rmtree(TEMP_HTML_DIR, ignore_errors=True)
    os.remove(script_path)

    # 统计结果
    total = 0
    for folder in sorted(day_folders):
        pngs = sorted(glob.glob(os.path.join(OUTPUT_DIR, folder, "*.png")))
        total += len(pngs)
        total_kb = sum(os.path.getsize(p) for p in pngs) / 1024
        names = ", ".join(os.path.splitext(os.path.basename(p))[0] for p in pngs)
        print(f"   📁 {folder}/ ({len(pngs)}张, {total_kb:.0f}KB): {names}")

    print(f"\n✅ 完成！共 {len(day_folders)} 天 {total} 张卡片")
