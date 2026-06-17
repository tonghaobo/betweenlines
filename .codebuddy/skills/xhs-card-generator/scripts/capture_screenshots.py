"""Step 1 截图捕获脚本：读取 content_calendar.md → 构造示例对话 → Playwright 网站输入 → 截图分析结果。

用法：python capture_screenshots.py [day_number]
  不带参数：处理所有天（Day 4-28）
  带参数：只处理指定天，如 python capture_screenshots.py 4
"""

import re, os, json, subprocess, sys

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
XHS_DIR = os.path.join(SELF_DIR, "..", "..", "..", "..", "xhs_docs")
SCREENSHOT_DIR = os.path.join(XHS_DIR, "screenshots")
CALENDAR_PATH = os.path.join(XHS_DIR, "content_calendar.md")
SITE_URL = "http://localhost:3000"


def ensure_dir():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def parse_calendar(target_day: int = None):
    """解析 content_calendar.md，提取每天标题、正文、截图需求。
    
    返回：List[dict]，每个 dict: {day, title, body, screenshots: [str]} 
    """
    if not os.path.exists(CALENDAR_PATH):
        raise FileNotFoundError(f"{CALENDAR_PATH} 不存在")

    with open(CALENDAR_PATH) as f:
        content = f.read()

    # 按 ## Day X 分割
    days = []
    blocks = re.split(r'\n(?=## Day \d+)', content)
    
    for block in blocks:
        m = re.match(r'## Day (\d+)', block.strip())
        if not m:
            continue
        day = int(m.group(1))
        if day < 4:  # Day 1-3 纯文字已发布，无需截图
            continue
        if target_day and day != target_day:
            continue

        # 提取标题
        title_m = re.search(r'\*\*标题[：:]\s*(.+?)\*\*', block)
        title = title_m.group(1).strip() if title_m else f"Day {day}"

        # 提取截图需求（如：[analysis_deep.png] 或 [截图: xxx.png]）
        screenshots = re.findall(r'\[([^\]]+\.png)\]', block)

        # 提取正文（标题之后、分隔线之前的内容）
        body_start = block.find("\n", block.find("**标题"))
        if body_start == -1:
            body_start = block.index("\n", block.index("## Day"))
        
        # 去掉标签行和链接行
        body_lines = []
        for line in block[body_start:].split("\n"):
            line = line.strip()
            if not line or line.startswith("##") or line.startswith("---"):
                continue
            if line.startswith("#") or line.startswith("🔗") or line.startswith("**标题"):
                continue
            body_lines.append(line)
        
        body = "\n".join(body_lines)

        days.append({
            "day": day,
            "title": title,
            "body": body,
            "screenshots": screenshots,
        })

    return days


# ═══════════════════════════════════════════════════════════════
# 示例对话构造规则
# 根据文案类型构造对应的示例聊天对话
# ═══════════════════════════════════════════════════════════════

DIALOG_TEMPLATES = {
    # Day 4：拐点检测 → 前期热后期冷的对话（至少20条，第23条附近拐点）
    4: [
        {
            "description": "拐点检测示例",
            "conversation": """她：早呀！今天怎么起这么早
我：哈哈睡不着就起来了
她：我也是！！昨晚追剧追到两点
我：追的啥剧啊
她：就那个新出的，超好看！推荐你
我：行啊，周末看看
她：你今天忙不忙
我：还行，上午有个会
她：加油加油，中午记得吃饭
我：你呢今天干嘛
她：我今天要去逛街，跟你说上次那家店打折
我：真的吗，买了啥
她：买了好多！给你看看
我：好看！
她：哈哈谢谢，你周末有什么计划
我：还没想好，可能在家待着
她：要不要一起出去？有个新开的咖啡馆
我：可以啊
她：那周六下午？
我：行
她：好的呀，到时候联系
我：周六几点方便
她：看情况吧
我：好的，那我等你消息
她：嗯
我：这两天忙吗
她：还好
我：那个咖啡馆我看了一下评价挺好的
她：嗯嗯
我：你最近在干嘛
她：没干嘛
我：周末还去吗
她：再说吧""",
            "target_screenshots": ["turning_point.png"],
        }
    ],
    # Day 6：回复走势预测 → "最近有点忙" 场景
    6: [
        {
            "description": "三种回复对比示例",
            "conversation": """我：周末一起吃饭吗？
她：最近有点忙～
我：那下周呢
她：下周也可能够呛
我：好的，那你先忙""",
            "target_screenshots": ["reply_trajectory.png"],
        }
    ],
    # Day 7：解题模式 → 分享感受被解题的对话
    7: [
        {
            "description": "解题模式示例",
            "conversation": """她：今天好累啊
我：那你早点睡，明天别喝咖啡了
她：不是困的那种累
我：那你可以试试去运动一下，运动完会好很多
她：……算了不说了
我：怎么了？我说错什么了吗""",
            "target_screenshots": ["analysis_deep.png"],
        }
    ],
    # Day 10：复盘 → 需要两次分析：先分析再复盘
    10: [
        {
            "description": "复盘-初次分析",
            "conversation": """同事：这个方案我们内部再讨论一下
我：好的，那我等您消息
同事：嗯
我：如果有需要补充的信息随时找我
同事：好的收到""",
            "target_screenshots": ["review_input.png"],
        }
    ],
    # Day 12：真实案例拆解
    12: [
        {
            "description": "三层问题示例",
            "conversation": """她：今天跟同事吵架了好烦
我：为什么吵，你跟我说说
她：工作分配的事
我：你可以跟领导反映一下，早解决比较好
她：算了不说了
我：好的知道了""",
            "target_screenshots": ["result_full.png"],
        }
    ],
    # Day 26：功能总览 → 用典型对话跑一遍拿到完整结果
    26: [
        {
            "description": "功能总览示例",
            "conversation": """她：今天好累
我：怎么了
她：没什么
我：那早点休息吧
她：嗯""",
            "target_screenshots": ["homepage.png", "result_full.png", "review_result.png"],
        }
    ],
}


def get_dialogs_for_day(day: int, entry: dict):
    """根据天的文案内容构造示例对话。
    
    如果有预定义模板则用模板，否则根据 body 内容 AI 构造。
    """
    if day in DIALOG_TEMPLATES:
        return DIALOG_TEMPLATES[day]
    
    # 通用规则：根据标题关键词推断场景
    title = entry["title"]
    body = entry["body"]
    
    # 默认构造一个通用对话
    dialogs = [{
        "description": f"Day {day} - {title}",
        "conversation": """她：最近好像挺忙的
我：还好，就是项目有点赶
她：哦
我：你呢，最近在忙什么
她：没啥
我：周末要不要一起吃饭
她：看情况吧""",
        "target_screenshots": [],
    }]
    return dialogs


# ═══════════════════════════════════════════════════════════════
# 截图执行（通过 Playwright MCP 或 Node.js 脚本）
# ═══════════════════════════════════════════════════════════════

def generate_capture_script(days_entries: list):
    """生成 Node.js Playwright 截图脚本，一次性处理所有需要截图的对话。"""
    
    tasks = []
    for entry in days_entries:
        day = entry["day"]
        dialogs = get_dialogs_for_day(day, entry)
        
        for di, dialog in enumerate(dialogs):
            tasks.append({
                "day": day,
                "index": di,
                "description": dialog["description"],
                "conversation": dialog["conversation"],
                "targets": dialog["target_screenshots"],
            })
    
    task_json = json.dumps(tasks, ensure_ascii=False, indent=2)
    
    script = f"""// 自动截图脚本：打开网站 → 输入对话 → 分析 → 截图
import {{ chromium }} from 'playwright';
import {{ mkdirSync, existsSync }} from 'fs';
import path from 'path';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const SCREENSHOT_DIR = '{SCREENSHOT_DIR}';
const SITE_URL = '{SITE_URL}';

if (!existsSync(SCREENSHOT_DIR)) {{
    mkdirSync(SCREENSHOT_DIR, {{ recursive: true }});
}}

const tasks = {task_json};

function sleep(ms) {{
    return new Promise(resolve => setTimeout(resolve, ms));
}}

async function captureAnalysisResults(page, task) {{
    // 等待分析结果加载
    await page.waitForSelector('[class*="Result"], [class*="ChatStatus"], [class*="analysis"]', 
        {{ timeout: 60000 }}).catch(() => {{}});
    await sleep(3000); // 等待渲染完成
    
    // 高清截图：网站强制 390px 移动端宽度，注入 transform scale 放大至 2063px
    await page.evaluate(() => {{
        const h = document.documentElement;
        h.style.transform = 'scale(2.3)';
        h.style.transformOrigin = 'top left';
        h.style.width = '897px';
    }});
    await sleep(500);
    
    const targets = task.targets;
    for (const target of targets) {{
        const filepath = path.join(SCREENSHOT_DIR, target);
        await page.screenshot({{ path: filepath, fullPage: true }});
        console.log(`  ✅ ${{target}}`);
    }}
    
    // 如果没有指定 target，截完整结果页
    if (targets.length === 0) {{
        const filepath = path.join(SCREENSHOT_DIR, `day${{String(task.day).padStart(2, '0')}}_result_${{task.index}}.png`);
        await page.screenshot({{ path: filepath, fullPage: true }});
        console.log(`  ✅ day${{String(task.day).padStart(2, '0')}}_result_${{task.index}}.png`);
    }}
}}

(async () => {{
    const browser = await chromium.launch({{ headless: true }});
    
    for (const task of tasks) {{
        console.log(`\\\\n📸 Day ${{task.day}}: ${{task.description}}`);
        
        const context = await browser.newContext({{ viewport: {{ width: 1440, height: 900 }} }});
        const page = await context.newPage();
        
        try {{
            // 1. 打开网站
            await page.goto(SITE_URL, {{ waitUntil: 'networkidle' }});
            console.log('  → 网站已打开');
            
            // 2. 输入对话
            const inputSelector = 'textarea, [contenteditable="true"], [role="textbox"]';
            await page.waitForSelector(inputSelector, {{ timeout: 10000 }});
            await page.fill(inputSelector, task.conversation);
            console.log('  → 对话已输入');
            
            // 3. 点击分析按钮
            const analyzeBtn = await page.$('button[type="submit"], button:has-text("分析"), button:has-text("Analyze")');
            if (analyzeBtn) {{
                await analyzeBtn.click();
                console.log('  → 分析已触发');
            }} else {{
                // 尝试按 Enter 提交
                await page.press(inputSelector, 'Enter');
                console.log('  → 按 Enter 提交');
            }}
            
            // 4. 等待结果 + 截图
            await captureAnalysisResults(page, task);
            
        }} catch (e) {{
            console.error(`  ❌ Day ${{task.day}}: ${{e.message}}`);
        }} finally {{
            await context.close();
        }}
    }}
    
    await browser.close();
    console.log('\\\\n🎉 截图完成！');
}})();
"""
    
    script_path = os.path.join(XHS_DIR, "_capture_screenshots.mjs")
    with open(script_path, "w") as f:
        f.write(script)
    return script_path


def main():
    ensure_dir()
    
    target_day = None
    if len(sys.argv) > 1:
        target_day = int(sys.argv[1])
        print(f"🎯 只处理 Day {target_day}")
    
    days = parse_calendar(target_day)
    if not days:
        print("❌ 未找到需要处理的文案数据")
        return
    
    print(f"📂 找到 {len(days)} 天的文案\n")
    
    for entry in days:
        dialogs = get_dialogs_for_day(entry["day"], entry)
        targets = []
        for d in dialogs:
            targets.extend(d["target_screenshots"])
        print(f"  Day {entry['day']}: {entry['title']}")
        print(f"    示例对话: {len(dialogs)} 组")
        print(f"    截图目标: {', '.join(targets) if targets else '(完整页面)'}")
    
    # 生成并运行截图脚本
    script_path = generate_capture_script(days)
    print(f"\n🚀 开始截图...\n")
    
    result = subprocess.run(
        ["node", script_path],
        cwd=XHS_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # 清理
    os.remove(script_path)
    print(f"\n✅ 截图已保存到 {SCREENSHOT_DIR}/")


if __name__ == "__main__":
    main()
