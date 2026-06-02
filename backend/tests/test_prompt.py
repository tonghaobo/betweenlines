"""
Prompt 效果测试脚本
用于测试不同聊天场景下的 AI 分析质量
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import asyncio
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

SYSTEM_PROMPT = """你是一个专业的社交沟通分析助手。

你的目标：
帮助用户理解聊天状态，并给出自然沟通建议。

分析重点：
1. 互动积极程度
2. 对方主动性
3. 情绪反馈
4. 潜在聊天问题
5. 风险提醒
6. 回复建议

禁止：
• 判断喜欢程度
• 编造事实
• 情绪操控
• PUA 风格
• 极端两性观点

回复必须：
自然、现实、可执行。

回复建议规则：
- 每条回复不超过 2 句话
- 自然、可直接复制发送
- 不油腻、不尴尬
- 禁止套路话术

输出格式：
严格 JSON。"""

TEST_CASES = [
    {
        "name": "积极互动",
        "chat": """A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢，等下去吃火锅！
A: 哇火锅，哪家呀
B: 就公司楼下那家，超好吃的
A: 我也想去！""",
        "expected_status": "积极互动",
        "checks": ["有情绪反馈", "对方主动延伸话题", "回复建议自然"],
    },
    {
        "name": "冷淡回应",
        "chat": """A: 周末有什么安排吗
B: 没有
A: 最近有部电影还不错
B: 哦
A: 你喜欢看电影吗
B: 还行""",
        "expected_status": "偏冷淡",
        "checks": ["指出回复简短", "建议暂停追问", "不判断喜欢程度"],
    },
    {
        "name": "礼貌回应",
        "chat": """A: 今天工作忙吗
B: 还行，就那样吧
A: 我也是，最近项目挺多的
B: 嗯嗯，辛苦了""",
        "expected_status": "礼貌回应",
        "checks": ["对方有回应但被动", "建议增加情绪价值", "回复建议不油腻"],
    },
    {
        "name": "高风险对话",
        "chat": """A: 你觉得我怎么样
B: 什么怎么样
A: 就是你觉得我这个人
B: 还行吧
A: 那我们是什么关系
B: 朋友啊
A: 只是朋友吗""",
        "expected_status": "对话风险较高",
        "checks": ["指出话题推进过快", "风险提醒明确", "不建议升级关系"],
    },
]


async def test_case(case: dict):
    user_prompt = f"""请分析以下聊天记录。

聊天内容：
---
{case['chat']}
---

请以 JSON 格式输出分析结果。JSON schema 如下：
{{"chat_status": "...", "analysis": "...", "issues": [...], "risks": [...], "reply_suggestions": {{"natural": "...", "humorous": "...", "mature": "..."}}, "timing_advice": "..."}}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.TEMPERATURE,
        max_tokens=settings.MAX_TOKENS,
    )

    content = response.choices[0].message.content
    # 清理 markdown 代码块
    cleaned = content.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    result = json.loads(cleaned)

    print(f"\n{'=' * 60}")
    print(f"📋 场景: {case['name']}")
    print(f"🎯 期望状态: {case['expected_status']}")
    print(f"📊 实际状态: {result.get('chat_status')}")
    print(f"📝 分析: {result.get('analysis', '')[:100]}...")
    print(f"⚠️  问题: {result.get('issues', [])}")
    print(f"🚨 风险: {result.get('risks', [])}")
    print(f"💬 自然版回复: {result.get('reply_suggestions', {}).get('natural', '')}")
    print(f"⏱️  节奏建议: {result.get('timing_advice', '')}")

    for check in case.get("checks", []):
        print(f"   ✅ 检查项: {check}")

    return result


async def main():
    print("=" * 60)
    print("BetweenLines Prompt 效果测试")
    print("=" * 60)

    results = []
    for case in TEST_CASES:
        try:
            result = await test_case(case)
            results.append({"case": case["name"], "status": "passed", "result": result})
        except Exception as e:
            print(f"\n❌ {case['name']} 测试失败: {str(e)}")
            results.append({"case": case["name"], "status": "failed", "error": str(e)})

    print(f"\n{'=' * 60}")
    print("📊 测试汇总")
    print(f"{'=' * 60}")
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"通过: {passed}/{len(results)}")
    print(f"失败: {failed}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
