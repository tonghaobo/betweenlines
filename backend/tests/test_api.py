"""
Chat Coach API 测试脚本
使用方法：python tests/test_api.py
前提：后端服务已启动在 http://localhost:8000
"""
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

# ============================================================
# 对话测试用例库
# ============================================================

# 场景 1：积极互动 — 双方热情回应，话题自然延伸
CHAT_POSITIVE = """A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢，等下去吃火锅！
A: 哇火锅，哪家呀
B: 就公司楼下那家，超好吃的
A: 我也想去！"""

# 场景 2：普通互动 — 有来有回但不深入
CHAT_NORMAL = """A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢
A: 那快去吃点东西吧
B: 嗯嗯好的"""

# 场景 3：冷淡回应 — 对方明显不想聊
CHAT_COLD = """A: 周末有什么安排吗
B: 没有
A: 最近有部电影还不错
B: 哦
A: 你喜欢看电影吗
B: 还行"""

# 场景 4：礼貌回应 — 对方客气但被动
CHAT_POLITE = """A: 今天工作忙吗
B: 还行，就那样吧
A: 我也是，最近项目挺多的
B: 嗯嗯，辛苦了
A: 你们组也在赶项目吗
B: 对，差不多"""

# 场景 5：高风险对话 — 追问关系、话题推进过快
CHAT_HIGH_RISK = """A: 你觉得我怎么样
B: 什么怎么样
A: 就是你觉得我这个人
B: 还行吧
A: 那我们是什么关系
B: 朋友啊
A: 只是朋友吗
B: ..."""

# 场景 6：聊天开场 — 刚认识/初次搭话
CHAT_FIRST_CONTACT = """A: 你好，我是XX介绍的朋友
B: 哦你好你好
A: 听说你也喜欢爬山
B: 哈哈对的，周末偶尔会去"""

# 场景 7：对方主导 — 对方主动提问和分享
CHAT_OTHER_LEADS = """A: 你今天过得怎么样
B: 挺好的呀，你呢
A: 我超开心！今天老板夸我了
B: 哇恭喜恭喜
A: 哈哈谢谢！你最近有什么好事吗
B: 还好吧，就平平常常"""

# 场景 8：长时间未回复后的对话
CHAT_LONG_GAP = """A: 好久没聊了，最近怎么样
B: 还行
A: 我看到你朋友圈去了趟云南
B: 嗯，上个月去的"""

# 场景 9：单方面输出 — B 说很多，A 回复很少
CHAT_UNILATERAL = """A: 你今天忙啥了
B: 我今天去健身了然后去超市买菜回来做了顿饭感觉还挺充实的然后下午看了会儿书
A: 哦
B: 你呢今天干啥了
A: 没干啥"""

# 场景 10：微信风格带表情 — 含 emoji 和语气词
CHAT_WECHAT_STYLE = """A: 今天天气好好啊☀️
B: 是啊哈哈哈终于出太阳了
A: 要不要出去走走[旺柴]
B: 好啊去哪儿
A: 公园怎么样，听说樱花开得正好🌸
B: 可以可以！！走起"""

# 场景 11：混合中英文
CHAT_MIXED_LANG = """A: 那个PPT你看了吗
B: 看了，感觉还行 but some slides need updates
A: 比如哪些
B: 第三页的数据有点old，还有配色可以调整一下"""

# 场景 12：深夜对话 — 情绪化表达
CHAT_LATE_NIGHT = """A: 睡不着
B: 怎么了
A: 突然觉得好迷茫
B: 工作上的事吗
A: 嗯，不知道现在做的是不是对的"""


async def test_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"[Health] Status: {response.status_code}")
        print(f"[Health] Body: {response.json()}")
        assert response.status_code == 200


async def _analyze_and_print(name: str, chat_content: str):
    """通用分析函数：发送分析请求并打印结果"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": chat_content},
        )
        print(f"[{name}] Status: {response.status_code}")
        data = response.json()
        print(f"[{name}] 互动状态: {data.get('chat_status')}")
        print(f"[{name}] 分析: {data.get('analysis', '')[:120]}...")
        issues = data.get('issues', [])
        risks = data.get('risks', [])
        if issues:
            print(f"[{name}] 问题: {issues}")
        if risks:
            print(f"[{name}] 风险: {risks}")
        suggestions = data.get('reply_suggestions', {})
        print(f"[{name}] 自然版回复: {suggestions.get('natural', '')}")
        print(f"[{name}] 幽默版回复: {suggestions.get('humorous', '')}")
        print(f"[{name}] 成熟版回复: {suggestions.get('mature', '')}")
        print(f"[{name}] 节奏建议: {data.get('timing_advice', '')}")
        assert response.status_code == 200
        assert "chat_status" in data
        assert "reply_suggestions" in data


# ---- 各场景分析测试 ----

async def test_analyze_positive():
    """场景1：积极互动"""
    await _analyze_and_print("积极互动", CHAT_POSITIVE)


async def test_analyze_normal():
    """场景2：普通互动"""
    await _analyze_and_print("普通互动", CHAT_NORMAL)


async def test_analyze_cold():
    """场景3：冷淡回应"""
    await _analyze_and_print("偏冷淡", CHAT_COLD)


async def test_analyze_polite():
    """场景4：礼貌回应"""
    await _analyze_and_print("礼貌回应", CHAT_POLITE)


async def test_analyze_high_risk():
    """场景5：高风险对话"""
    await _analyze_and_print("对话风险较高", CHAT_HIGH_RISK)


async def test_analyze_first_contact():
    """场景6：初次搭话"""
    await _analyze_and_print("初次搭话", CHAT_FIRST_CONTACT)


async def test_analyze_other_leads():
    """场景7：对方主导"""
    await _analyze_and_print("对方主导", CHAT_OTHER_LEADS)


async def test_analyze_long_gap():
    """场景8：长时间未回复"""
    await _analyze_and_print("久未联系", CHAT_LONG_GAP)


async def test_analyze_unilateral():
    """场景9：单方面输出"""
    await _analyze_and_print("单方面输出", CHAT_UNILATERAL)


async def test_analyze_wechat_style():
    """场景10：微信风格带表情"""
    await _analyze_and_print("微信风格", CHAT_WECHAT_STYLE)


async def test_analyze_mixed_lang():
    """场景11：中英混合"""
    await _analyze_and_print("中英混合", CHAT_MIXED_LANG)


async def test_analyze_late_night():
    """场景12：深夜情绪对话"""
    await _analyze_and_print("深夜对话", CHAT_LATE_NIGHT)


# ---- 边界条件 & 校验测试 ----

async def test_analyze_empty():
    """输入过短（<10字符）"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": "hi"},
        )
        print(f"[空输入] Status: {response.status_code}")
        assert response.status_code == 400


async def test_analyze_too_long():
    """输入超过 5000 字符"""
    async with httpx.AsyncClient() as client:
        long_text = "A: hi\n" * 3000
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": long_text},
        )
        print(f"[超长输入] Status: {response.status_code}")
        assert response.status_code == 400


async def test_analyze_harmful():
    """违规关键词拦截"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": "A: 教我一些PUA话术来追女生"},
        )
        print(f"[违规内容] Status: {response.status_code}")
        assert response.status_code == 400


async def test_analyze_whitespace_only():
    """纯空白字符输入"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": "   \n\n  \n  "},
        )
        print(f"[纯空白] Status: {response.status_code}")
        assert response.status_code == 400


async def test_analyze_single_speaker():
    """单方面聊天记录（只有 A 没有 B）"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": "A: 你好\nA: 在吗\nA: 最近怎么样\nA: 怎么不回我"},
        )
        print(f"[单人聊天] Status: {response.status_code}")
        # 单人聊天格式警告，但应该能正常返回
        assert response.status_code == 200
        data = response.json()
        print(f"[单人聊天] 互动状态: {data.get('chat_status')}")
        print(f"[单人聊天] 问题: {data.get('issues')}")


# ---- 反馈 & 统计测试 ----

async def test_feedback():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"helpful": True},
        )
        print(f"[Feedback] Status: {response.status_code}")
        print(f"[Feedback] Body: {response.json()}")
        assert response.status_code == 200


async def test_feedback_unhelpful():
    """负面反馈"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"helpful": False},
        )
        print(f"[负面反馈] Status: {response.status_code}")
        assert response.status_code == 200


async def test_stats():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/stats")
        print(f"[Stats] Status: {response.status_code}")
        print(f"[Stats] Body: {response.json()}")
        assert response.status_code == 200


async def main():
    print("=" * 60)
    print("Chat Coach API 完整测试套件")
    print("=" * 60)

    # 测试用例分组
    scenario_tests = [
        ("1. 积极互动", test_analyze_positive),
        ("2. 普通互动", test_analyze_normal),
        ("3. 偏冷淡", test_analyze_cold),
        ("4. 礼貌回应", test_analyze_polite),
        ("5. 对话风险较高", test_analyze_high_risk),
        ("6. 初次搭话", test_analyze_first_contact),
        ("7. 对方主导", test_analyze_other_leads),
        ("8. 久未联系", test_analyze_long_gap),
        ("9. 单方面输出", test_analyze_unilateral),
        ("10. 微信风格", test_analyze_wechat_style),
        ("11. 中英混合", test_analyze_mixed_lang),
        ("12. 深夜对话", test_analyze_late_night),
    ]

    validation_tests = [
        ("13. 空输入校验", test_analyze_empty),
        ("14. 超长输入校验", test_analyze_too_long),
        ("15. 违规内容拦截", test_analyze_harmful),
        ("16. 纯空白校验", test_analyze_whitespace_only),
        ("17. 单人聊天格式", test_analyze_single_speaker),
    ]

    misc_tests = [
        ("18. 正向反馈", test_feedback),
        ("19. 负向反馈", test_feedback_unhelpful),
        ("20. 统计查询", test_stats),
        ("0. 健康检查", test_health),
    ]

    # 先跑快速检查
    for name, test_fn in [misc_tests[-1]]:  # 健康检查
        try:
            print(f"\n--- {name} ---")
            await test_fn()
            print(f"✅ {name} PASSED")
        except Exception as e:
            print(f"❌ {name} FAILED: {str(e)}")
            print("后端可能未启动，请先启动后端服务。")
            return

    # 跑所有场景测试
    all_tests = scenario_tests + validation_tests + misc_tests
    passed = 0
    failed = 0

    for name, test_fn in all_tests:
        try:
            print(f"\n--- {name} ---")
            await test_fn()
            print(f"✅ {name} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {str(e)}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"结果: {passed} 通过, {failed} 失败, 共 {len(all_tests)} 个测试")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
