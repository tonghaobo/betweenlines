"""Benchmark models on speed + quality, output ranked by combined score.

Usage: python tests/benchmark_models.py
"""
import os, sys, time, json, asyncio
from openai import AsyncOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(override=True)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

TEXT_MODELS = [
    "doubao-seed-2-0-pro-260215",
    "doubao-seed-1-8-251228",
    "doubao-1-5-pro-32k-250115",
    "doubao-seed-1-6-flash-250828",
    "doubao-seed-2-0-mini-260428",
    "doubao-1-5-lite-32k-250115",
]

# Test scenario: normal interaction (should be "普通互动" / "normal")
TEST_CHAT = """我: 今天在干嘛呀
她: 刚下班，好累哈哈
我: 辛苦啦，吃饭了吗
她: 还没呢，等下去吃火锅！
我: 哇火锅，哪家呀
她: 就公司楼下那家，超好吃的
我: 我也想去！"""

SYSTEM_PROMPT = """你是社交沟通分析助手。分析聊天氛围并给回复建议。
对方用"他/她:"，用户用"我:"。
分析：1.互动度 2.对方主动性 3.情绪反馈 4.问题 5.风险
禁止：判断喜欢、编造、情感操控、PUA
回复≤2句，自然可发送。
只输出JSON。"""

USER_PROMPT = f"""场景：恋爱/暧昧。关注：主动性、情绪氛围、节奏。禁止：绝对判断、情感操控。

聊天：
---
{TEST_CHAT}
---

输出JSON(不要markdown包裹):
{{"chat_status":"积极互动|普通互动|礼貌回应|偏冷淡|对话风险较高","analysis":"分析","issues":[],"risks":[],"reply_suggestions":{{"natural":"回复","humorous":"回复","mature":"回复"}},"timing_advice":"建议"}}

要求：必须选一个chat_status，issues/risks空则[]，回复≤2句话自然可发送。禁止判断喜欢/PUA。"""


def score_quality(raw: str) -> tuple[int, str]:
    """Score output quality: 0-40 points. Higher = better.
    
    Returns (score, notes).
    """
    score = 0
    notes = []

    # ── 1. Valid JSON (0 or 15 points, hard requirement) ──
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        idx = cleaned.find("\n")
        cleaned = cleaned[idx + 1:] if idx != -1 else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        data = json.loads(cleaned)
        score += 15
    except Exception:
        return (0, "INVALID JSON")

    # ── 2. chat_status correctness (8 points) ──
    status = data.get("chat_status", "").strip().lower()
    expected = ["积极互动", "普通互动", "positive", "normal", "engaged"]
    if any(s in status for s in expected):
        score += 8
        notes.append("status ✓")
    elif status in ("礼貌回应", "偏冷淡", "polite", "cold"):
        score += 4
        notes.append(f"status borderline: {status}")
    else:
        notes.append(f"status WRONG: {status}")

    # ── 3. Analysis quality (5 points) ──
    analysis = data.get("analysis", "")
    if len(analysis) >= 30 and not any(w in analysis.lower() for w in ("喜欢你", "love", "pua", "把妹")):
        score += 5
        notes.append("analysis ✓")
    else:
        notes.append(f"analysis weak ({len(analysis)} chars)")

    # ── 4. Reply suggestions (10 points) ──
    suggestions = data.get("reply_suggestions", {})
    natural = suggestions.get("natural", "")
    humorous = suggestions.get("humorous", "")
    mature = suggestions.get("mature", "")
    reply_score = 0
    if len(natural) >= 5 and len(natural) <= 80:
        reply_score += 3
    if len(humorous) >= 5 and len(humorous) <= 80:
        reply_score += 3
    if len(mature) >= 5 and len(mature) <= 80:
        reply_score += 3
    if natural != humorous and humorous != mature:
        reply_score += 1
    score += reply_score
    if reply_score >= 9:
        notes.append("replies ✓")
    else:
        notes.append(f"replies weak ({reply_score}/10)")

    # ── 5. No banned content (2 points) ──
    full_text = json.dumps(data, ensure_ascii=False).lower()
    banned = ["绝对判断", "喜欢你", "她喜欢你", "pua", "把妹", "泡妞"]
    if not any(b in full_text for b in banned):
        score += 2
        notes.append("no banned content")

    return (score, "; ".join(notes))


def fmt_model(model: str) -> str:
    parts = [p for p in model.split("-") if any(k in p for k in ("seed", "pro", "lite", "flash", "mini", "2.0", "1.8", "1.5"))]
    return "-".join(parts)


async def main():
    if not API_KEY:
        print("ERROR: API_KEY not set")
        return

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    results = []

    print("=" * 75)
    print("  BetweenLines 模型速度+质量综合测试")
    print("=" * 75)

    for model in TEXT_MODELS:
        name = fmt_model(model)
        print(f"\n[{name}]")
        durations = []
        qualities = []
        q_notes = []

        for run in range(2):
            t0 = time.time()
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": USER_PROMPT},
                    ],
                    temperature=0.7, max_tokens=400,
                )
                raw = resp.choices[0].message.content or ""
                d = time.time() - t0
                q, notes = score_quality(raw)
                durations.append(d)
                qualities.append(q)
                q_notes.append(notes)
                print(f"  run{run+1}: {d:.1f}s  quality={q}/40  {notes}")
            except Exception as e:
                print(f"  run{run+1}: FAILED - {str(e)[:80]}")
                durations.append(None)
                qualities.append(0)

        valid = [(d, q, n) for d, q, n in zip(durations, qualities, q_notes) if d is not None]
        if not valid:
            results.append((name, "FAILED", 0, 0, 0, "-"))
            continue

        avg_speed = sum(d for d, _, _ in valid) / len(valid)
        avg_quality = sum(q for _, q, _ in valid) / len(valid)
        best_q = max(q for _, q, _ in valid)
        speed_norm = max(1.0, 20.0 / max(avg_speed, 0.5))  # cap at 20
        combined = round(avg_quality * 0.7 + speed_norm * 0.3, 1)
        results.append((name, model, avg_speed, avg_quality, best_q, combined, q_notes[-1]))

    # ── Rank by combined score ──
    ranked = sorted(results, key=lambda x: x[5], reverse=True)

    print("\n\n" + "=" * 75)
    print("  综合排名 (质量70% + 速度30%)")
    print("=" * 75)
    print(f"  {'排名':<4} {'模型':<25} {'速度':>6} {'质量':>5} {'综合':>5}")
    print("-" * 75)
    for i, (name, _, speed, quality, _, combined, _) in enumerate(ranked, 1):
        flag = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f" {i}."))
        print(f"  {flag}  {name:<25} {speed:>5.1f}s  {quality:>4.0f}/40 {combined:>5.1f}")

    print(f"\n  💡 推荐 TEXT_MODELS:")
    rec = ",".join([m for _, m, _, _, _, _, _ in ranked])
    print(f"  TEXT_MODELS={rec}")


if __name__ == "__main__":
    asyncio.run(main())
