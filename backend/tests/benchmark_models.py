"""Benchmark all available text & vision models for speed comparison.

Usage: python tests/benchmark_models.py
"""
import os
import sys
import time
import json
import base64
import asyncio
from openai import AsyncOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

# ── Models to benchmark ──
TEXT_MODELS = [
    "doubao-seed-2-0-pro-260215",
    "doubao-seed-1-8-251228",
    "doubao-1-5-pro-32k-250115",
    "doubao-seed-1-6-flash-250828",
    "doubao-seed-2-0-mini-260428",
    "doubao-1-5-lite-32k-250115",
]

VISION_MODELS = [
    "doubao-seed-1-6-vision-250815",
    "doubao-1-5-vision-pro-32k-250115",
    "doubao-1.5-vision-lite-250315",
]

# ── Test chat content (normal interaction, ~150 chars) ──
TEST_CHAT = """我: 今天在干嘛呀
她: 刚下班，好累哈哈
我: 辛苦啦，吃饭了吗
她: 还没呢，等下去吃火锅！
我: 哇火锅，哪家呀
她: 就公司楼下那家，超好吃的
我: 我也想去！"""

# ── System / User prompts (matches production) ──
SYSTEM_PROMPT = """你是社交沟通分析助手。分析聊天氛围并给回复建议。
对方用"他/她:"，用户用"我:"。
分析：1.互动度 2.对方主动性 3.情绪反馈 4.问题 5.风险
禁止：判断喜欢、编造、情感操控、PUA
回复≤2句，自然可发送。
只输出JSON。"""

USER_PROMPT_TEMPLATE = """场景：恋爱/暧昧。关注：主动性、情绪氛围、节奏。禁止：绝对判断、情感操控。

聊天：
---
{chat}
---

输出JSON(不要markdown包裹):
{{"chat_status":"积极互动|普通互动|礼貌回应|偏冷淡|对话风险较高","analysis":"分析","issues":[],"risks":[],"reply_suggestions":{{"natural":"回复","humorous":"回复","mature":"回复"}},"timing_advice":"建议"}}

要求：必须选一个chat_status，issues/risks空则[]，回复≤2句话自然可发送。禁止判断喜欢/PUA。"""

SCREENSHOT_PROMPT = """你是一个聊天截图文字提取助手。从聊天截图中提取所有可见的聊天消息。

要求：
1. 按时间顺序提取每条消息
2. 区分发言人：对方用"他/她:"，用户自己用"我:"标注
3. 保留表情符号文字描述（如 [笑哭]）
4. 忽略系统提示（如"对方正在输入"、时间戳等）
5. 仅输出聊天文字内容
"""


def generate_test_screenshot() -> bytes:
    """Create a minimal test screenshot using Python stdlib (no PIL)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (400, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        lines = [
            "她: 刚下班，好累哈哈",
            "我: 辛苦啦，吃饭了吗",
            "她: 还没呢，去次火锅",
        ]
        y = 10
        for line in lines:
            draw.text((10, y), line, fill=(50, 50, 50))
            y += 40
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback: minimal 1x1 white PNG
        print("  ⚠ PIL not available, using minimal test image")
        # 1x1 white pixel PNG
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
        return png


async def benchmark_text(model: str, client: AsyncOpenAI, runs: int = 3) -> dict:
    """Benchmark a text model with multiple runs, return avg/min/max."""
    durations = []
    for i in range(runs):
        t0 = time.time()
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(chat=TEST_CHAT)},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            output_len = len(response.choices[0].message.content or "")
        except Exception as e:
            print(f"    ✗ run {i+1} failed: {str(e)[:80]}")
            durations.append(None)
            continue
        d = time.time() - t0
        durations.append(d)
        print(f"    run {i+1}: {d:.2f}s (output {output_len} chars)")

    valid = [d for d in durations if d is not None]
    if not valid:
        return {"model": model, "avg": None, "min": None, "max": None, "runs": 0, "error": "all failed"}
    return {
        "model": model,
        "avg": round(sum(valid) / len(valid), 2),
        "min": round(min(valid), 2),
        "max": round(max(valid), 2),
        "runs": len(valid),
    }


async def benchmark_vision(model: str, client: AsyncOpenAI, image_bytes: bytes, runs: int = 2) -> dict:
    """Benchmark a vision model."""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    durations = []
    for i in range(runs):
        t0 = time.time()
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                            {"type": "text", "text": SCREENSHOT_PROMPT},
                        ],
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            output_len = len(response.choices[0].message.content or "")
        except Exception as e:
            print(f"    ✗ run {i+1} failed: {str(e)[:80]}")
            durations.append(None)
            continue
        d = time.time() - t0
        durations.append(d)
        print(f"    run {i+1}: {d:.2f}s (output {output_len} chars)")

    valid = [d for d in durations if d is not None]
    if not valid:
        return {"model": model, "avg": None, "min": None, "max": None, "runs": 0, "error": "all failed"}
    return {
        "model": model,
        "avg": round(sum(valid) / len(valid), 2),
        "min": round(min(valid), 2),
        "max": round(max(valid), 2),
        "runs": len(valid),
    }


def format_model_name(model: str) -> str:
    """Shorten model name for display."""
    parts = model.split("-")
    key_parts = []
    for p in parts:
        if any(k in p for k in ["seed", "pro", "lite", "flash", "mini", "vision", "1.5", "1.8", "2.0"]):
            key_parts.append(p)
    return "-".join(key_parts) if key_parts else model


async def main():
    if not API_KEY or not API_KEY.startswith("ark-"):
        print("ERROR: OPENAI_API_KEY not set or invalid.")
        return

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    print("=" * 70)
    print("  BetweenLines 模型速度基准测试")
    print("=" * 70)

    # ── Text models ──
    print(f"\n📝 文本模型 ({len(TEXT_MODELS)} 个，每个跑 3 次)")
    print("-" * 70)
    text_results = []
    for model in TEXT_MODELS:
        print(f"\n  [{format_model_name(model)}]")
        result = await benchmark_text(model, client, runs=3)
        text_results.append(result)

    # ── Vision models ──
    print(f"\n\n🖼️ 视觉模型 ({len(VISION_MODELS)} 个，每个跑 2 次)")
    print("-" * 70)
    print("  生成测试截图...")
    screenshot = generate_test_screenshot()
    print(f"  截图大小: {len(screenshot)} bytes")

    vision_results = []
    for model in VISION_MODELS:
        print(f"\n  [{format_model_name(model)}]")
        result = await benchmark_vision(model, client, screenshot, runs=2)
        vision_results.append(result)

    # ── Summary ──
    print("\n\n" + "=" * 70)
    print("  📊 文本模型速度排名 (按 avg 升序)")
    print("=" * 70)
    valid_text = sorted([r for r in text_results if r["avg"] is not None], key=lambda x: x["avg"])
    for i, r in enumerate(valid_text, 1):
        flag = "⚡" if r["avg"] < 2 else ("✅" if r["avg"] < 4 else "🐌")
        name = format_model_name(r['model'])
        print(f"  {i}. {flag} {name:35s} avg={r['avg']:.2f}s  min={r['min']:.2f}s  max={r['max']:.2f}s")

    print(f"\n  📊 视觉模型速度排名")
    print("-" * 70)
    valid_vision = sorted([r for r in vision_results if r["avg"] is not None], key=lambda x: x["avg"])
    for i, r in enumerate(valid_vision, 1):
        flag = "⚡" if r["avg"] < 3 else ("✅" if r["avg"] < 5 else "🐌")
        name = format_model_name(r['model'])
        print(f"  {i}. {flag} {name:35s} avg={r['avg']:.2f}s  min={r['min']:.2f}s  max={r['max']:.2f}s")

    # ── Recommended order ──
    print(f"\n\n  💡 推荐 TEXT_MODELS 配置:")
    names = [r['model'] for r in valid_text]
    print(f"  TEXT_MODELS={','.join(names)}")

    print(f"\n  💡 推荐 VISION_MODELS 配置:")
    names = [r['model'] for r in valid_vision]
    print(f"  VISION_MODELS={','.join(names)}")


if __name__ == "__main__":
    asyncio.run(main())
