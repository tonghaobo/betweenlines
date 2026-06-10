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

SYSTEM_PROMPT = """你是社交沟通分析专家。你的任务是基于聊天记录，客观分析双方互动质量，并给出贴合原文的回复建议。

分析步骤（请按顺序思考）：
1. 整体感知：消息轮次、回复间隔、总体情绪基调
2. 双方对比：各发言几条？谁主导话题？是否互相回应？
3. 情绪识别：对方每句话背后的情绪（热情/平淡/回避/不耐烦）
4. 问题定位：是否存在冷场、敷衍、误解、话题枯竭？
5. 综合判断：给出 chat_status，确保与具体观察一致

输出质量要求：
- analysis：3-5 句具体观察，每句都应有原文支撑，禁止泛泛而谈（如"对方不太积极"应改为"对方连续回复都是单字'嗯'，无明显话题延伸"）
- issues：列出具体问题，每条≤20字，必须基于原文而非猜测
- risks：列出潜在风险（氛围恶化/误解加深/时机不当），空则为[]
- reply_suggestions：每种风格≤2句，必须呼应聊天中最新的1-2条消息，让人可以直接发送
- timing_advice：给出可操作的具体建议（如"等半小时再发"、"换一个话题方向"），而非"保持节奏"之类的废话

严格禁止：
- 判断对方是否喜欢你
- 任何 PUA / 情感操控话术
- 编造聊天记录中不存在的事实
- 使用模板化套话（如"祝你们越来越好"）
- 代替用户做决定
- 制造焦虑或恐吓

只输出纯 JSON，不要包裹在 markdown 代码块中。"""

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

输出JSON(不要markdown包裹):
{{"chat_status":"积极互动|普通互动|礼貌回应|偏冷淡|对话风险较高","analysis":"3-5句具体分析，每句引用原文","issues":["具体问题1","具体问题2"],"risks":[],"reply_suggestions":{{"natural":"回复，呼应最新消息","humorous":"回复，呼应最新消息","mature":"回复，呼应最新消息"}},"timing_advice":"可操作的具体建议"}}

质量要求：
- analysis 每句话都要有原文支撑，禁止泛泛而谈
- reply_suggestions 必须呼应聊天中最新的消息内容，可直接发送
- timing_advice 必须具体可操作，禁止"保持节奏"等套话
- 禁止判断喜欢/PUA/编造事实/模板化套话"""

    response = await client.chat.completions.create(
        model=settings.TEXT_MODELS[0],
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
