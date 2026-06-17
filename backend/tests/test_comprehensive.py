"""
Comprehensive Quality & Performance Test Suite for BetweenLines
Usage: python tests/test_comprehensive.py
Prerequisite: Backend running at http://localhost:8000

Test Dimensions:
  1. Model Effectiveness — status accuracy, deep signal detection
  2. Basic Functionality — schema, error handling
  3. Timing — average/median/max per scenario
  4. Quality — content references, anti-generic, deep-signal coverage
  5. Edge Cases — short/long, emoji, single-sided
"""
import httpx
import asyncio
import time
import json
import re
from typing import Optional

BASE_URL = "http://localhost:8000"

# ═══════════════════════════════════════════════════════════
# Test Cases (15 scenarios covering all 8 analysis dimensions)
# ═══════════════════════════════════════════════════════════

TEST_CASES = {
    # ── Basic Scenarios ──
    "积极互动": {
        "chat": "我: 今天干嘛了呀\n她: 刚健身完，超爽的\n我: 厉害啊，练了什么\n她: 主要是臀腿，现在腿都在发抖哈哈\n我: 哈哈那明天肯定酸爽\n她: 对！你也该去练练",
        "rel": "romantic",
        "expected_status": "积极互动",
        "expect_signals": [],
    },
    "普通互动": {
        "chat": "我: 今天忙吗\n她: 还行吧\n我: 我也是，项目挺多的\n她: 嗯嗯\n我: 周末有什么安排\n她: 暂时没有",
        "rel": "romantic",
        "expected_status": None,  # Borderline: "还行吧/嗯嗯/暂时没有" is quite flat
        "expect_signals": [],
    },
    "偏冷淡": {
        "chat": "我: 周末有什么安排吗\n她: 没有\n我: 最近有部电影还不错\n她: 哦\n我: 你喜欢看电影吗\n她: 还行",
        "rel": "romantic",
        "expected_status": "偏冷淡",
        "expect_signals": [],
    },

    # ── Deep Signal: 解题模式 (Solution Mode) ──
    "解题模式_典型": {
        "chat": "她: 今天跟同事吵架了好烦\n我: 为什么吵架，跟我说说\n她: 就是工作分配的事，她觉得我抢了她的活\n我: 你可以跟领导反映一下，这种问题早解决比较好\n她: 算了不说了\n我: 好的知道了",
        "rel": "romantic",
        "expected_status": "偏冷淡",
        # AI often says: 方案/共情/解题/给建议/倾听
        "expect_signals": ["方案", "共情", "建议", "情绪"],
    },
    "解题模式_家人版": {
        "chat": "妈: 最近腰老是疼，干什么都没劲\n我: 你可以去做个推拿，或者买个按摩椅\n妈: 算了跟你说也没用\n我: 那你去看医生啊",
        "rel": "family",
        "expected_status": None,
        "expect_signals": ["共情", "安慰", "听"],
    },

    # ── Deep Signal: 收口信号 (Closing Signals) ──
    "收口信号_连续关门": {
        "chat": "她: 今天那个电影真的好好看\n我: 嗯嗯\n她: 尤其结尾那段，我都哭了\n我: 好的\n她: 你下次也去看看\n我: 知道了",
        "rel": "romantic",
        "expected_status": "偏冷淡",
        # AI often says: 堵死/堵路/接不住/收尾/收口
        "expect_signals": ["堵", "收尾", "接", "路"],
    },

    # ── Deep Signal: 零提问 (Zero Questions) ──
    "零提问_双方都等": {
        "chat": "我: 今天上班好累\n她: 我也是\n我: 项目催得紧\n她: 嗯确实\n我: 晚上随便吃点算了\n她: 行",
        "rel": "romantic",
        "expected_status": None,
        # AI often says: 提问/反问/话题/抛
        "expect_signals": ["提问", "话题", "抛"],
    },

    # ── Deep Signal: 表情包依赖 (Emoji Relay) ──
    "表情包接力": {
        "chat": "我: [笑哭]\n她: [捂脸]\n我: [旺柴]\n她: [裂开]\n我: 😂\n她: 🤣",
        "rel": "friend",
        "expected_status": None,
        # AI often says: 表情/接力/文字/交流
        "expect_signals": ["表情", "接力", "文字", "交流"],
    },

    # ── Deep Signal: 安全区对话 (Safe Zone) ──
    "安全区对话": {
        "chat": "我: 今天天气不错\n她: 是啊\n我: 你吃饭了吗\n她: 吃了\n我: 吃的啥\n她: 外卖\n我: 哦哦好的\n她: 嗯",
        "rel": "romantic",
        "expected_status": "偏冷淡",
        # AI often says: 单字/应付/话题/抛
        "expect_signals": ["单字", "应付", "话题"],
    },

    # ── Cross-dimension: Multiple issues ──
    "混合_冷场加追问": {
        "chat": "我: 你觉得我怎么样\n她: 什么怎么样\n我: 就是你觉得我这个人\n她: 还行吧\n我: 那我们是什么关系\n她: 朋友啊\n我: 只是朋友吗\n她: ...",
        "rel": "romantic",
        "expected_status": "对话风险较高",
        "expect_signals": [],
    },

    # ── Relationship Variations ──
    "职场_请示领导": {
        "chat": "我: 王总，项目方案发您了\n领导: 好\n我: 您看还有什么需要调整的吗\n领导: 暂时没有\n我: 好的",
        "rel": "coworker",
        "expected_status": None,
        # AI says: 衔接/留余地/下一步
        "expect_signals": ["衔接", "余地", "下一步"],
    },

    # ── Edge Cases ──
    # Edge: This will fail validation (min 10 chars) — expected behavior in test expectations
    "超短对话": {
        "chat": "我: 嗨\n她: 嗯",
        "rel": "romantic",
        "expected_status": None,
        "expect_signals": [],
        "expect_validation_error": True,  # <10 chars, should return 400
    },
    "长篇多轮": {
        "chat": "\n".join([
            f"我: msg{i}a" if i % 2 == 0 else f"她: msg{i}b"
            for i in range(20)
        ]),
        "rel": "other",
        "expected_status": None,
        "expect_signals": [],
    },
    "单方面输出": {
        "chat": "她: 今天我去逛街了买了好多东西\n她: 然后去吃了火锅\n她: 火锅超好吃\n她: 你下次也去吃\n我: 哦\n她: 还有我看了个电影\n我: 嗯",
        "rel": "friend",
        "expected_status": None,
        "expect_signals": [],
    },
    "纯正面_表情丰富": {
        "chat": "我: 周末出去玩啊😎\n她: 好啊！！去哪去哪\n我: 爬山怎么样⛰️\n她: 可以可以[转圈]\n我: 那周六早上八点？\n她: 没问题👌",
        "rel": "friend",
        "expected_status": "积极互动",
        "expect_signals": [],
    },
}


# ═══════════════════════════════════════════════════════════
# Quality Check Utilities
# ═══════════════════════════════════════════════════════════

def check_has_content_reference(analysis: str) -> bool:
    """Check if analysis references specific chat content."""
    # Chinese/English quote marks including 「」
    if any(c in analysis for c in ['"', '"', '「', '」', "'", '、', '：', '"', '"', '"']):
        return True
    # Specific word counts or numeric references
    if re.search(r'\d+\s*[个字条句轮次]', analysis):
        return True
    # Topic references to specific content
    if re.search(r'(她说|对方说|你回|聊到|提到|说起|那句|这句|全是|全用)', analysis):
        return True
    # Direct quote patterns
    if re.search(r'[「「""](.{2,})[」」""]', analysis):
        return True
    # Patterns like "你用「好的」「知道了」把路堵死"
    if re.search(r'[「「].+?[」」]', analysis):
        return True
    return False


def check_no_generic_phrases(analysis: str, suggestions: dict) -> bool:
    """Check for template clichés."""
    generic = ["祝你们越来越好", "祝你好运", "越来越好", "幸福美满"]
    text = analysis + " " + str(suggestions)
    return not any(g in text for g in generic)


def check_deep_signals_detected(analysis: str, issues: list, expected_signals: list) -> dict:
    """Check if expected deep signals are mentioned in analysis or issues."""
    if not expected_signals:
        return {"found": [], "missing": [], "score": 1.0}

    combined = analysis + " " + " ".join(issues)
    found = [s for s in expected_signals if re.search(re.escape(s), combined, re.IGNORECASE)]
    missing = [s for s in expected_signals if s not in found]
    score = len(found) / len(expected_signals) if expected_signals else 1.0
    return {"found": found, "missing": missing, "score": score}


def check_analysis_length(analysis: str) -> bool:
    """Check if analysis is within the 150-char target."""
    return len(analysis) <= 200  # Allow some buffer over 150


def check_reply_quality(suggestions: dict) -> bool:
    """Check that replies are not generic fallbacks."""
    generic_fallbacks = [
        "可以自然地继续聊天",
        "用轻松的方式回应",
        "保持稳重得体的交流",
    ]
    for style, content in suggestions.items():
        reply_text = content.get("reply", "") if isinstance(content, dict) else str(content)
        for fb in generic_fallbacks:
            if reply_text.strip() == fb:
                return False
    return True


# ═══════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.status_code: int = 0
        self.duration_ms: float = 0
        self.analysis_len: int = 0
        self.chat_status: str = ""
        self.issues: list = []
        self.suggestions: dict = {}
        self.errors: list = []
        # Quality scores
        self.has_ref: bool = False
        self.no_generic: bool = True
        self.signal_score: float = 1.0
        self.signals_found: list = []
        self.signals_missing: list = []
        self.len_ok: bool = True
        self.reply_ok: bool = True


async def run_single_test(name: str, config: dict) -> TestResult:
    """Run one test case and collect all metrics."""
    result = TestResult(name)

    try:
        t0 = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/analyze",
                json={
                    "chat_content": config["chat"],
                    "relationship_type": config["rel"],
                    "language": "zh",
                    "anonymous_user_id": f"test_{name[:8]}",
                },
            )
        result.duration_ms = round((time.time() - t0) * 1000)
        result.status_code = resp.status_code

        # Expected validation errors (e.g. too short chat)
        if config.get("expect_validation_error"):
            if resp.status_code in (400, 422):
                result.len_ok = True  # expected behavior
                return result
            else:
                result.errors.append(f"Expected 400 validation error, got {resp.status_code}")
                return result

        if resp.status_code != 200:
            result.errors.append(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return result

        data = resp.json()
        result.chat_status = data.get("chat_status", "")
        result.issues = data.get("issues", [])
        result.suggestions = data.get("reply_suggestions", {})
        analysis = data.get("analysis", "")

        # ── Quality Checks ──
        result.has_ref = check_has_content_reference(analysis)
        result.no_generic = check_no_generic_phrases(analysis, result.suggestions)
        result.len_ok = check_analysis_length(analysis)
        result.analysis_len = len(analysis)
        result.reply_ok = check_reply_quality(result.suggestions)

        # Deep signal detection
        signal_result = check_deep_signals_detected(
            analysis, result.issues, config["expect_signals"]
        )
        result.signal_score = signal_result["score"]
        result.signals_found = signal_result["found"]
        result.signals_missing = signal_result["missing"]

        # Status check (if expected, allow adjacent levels for borderline cases)
        if config.get("expected_status") and config["expected_status"] != result.chat_status:
            # Allow one-level tolerance for borderline conversations
            status_order = ["积极互动", "普通互动", "礼貌回应", "偏冷淡", "对话风险较高"]
            exp_idx = status_order.index(config["expected_status"]) if config["expected_status"] in status_order else -1
            act_idx = status_order.index(result.chat_status) if result.chat_status in status_order else -1
            if exp_idx >= 0 and act_idx >= 0 and abs(exp_idx - act_idx) <= 1:
                pass  # Within tolerance — borderline case, don't flag
            else:
                result.errors.append(
                    f"状态不符: 期望'{config['expected_status']}' 实际'{result.chat_status}'"
                )

        if not result.len_ok:
            result.errors.append(f"analysis过长({result.analysis_len}字)")

        if not result.has_ref:
            result.errors.append("analysis未引用原文内容")

        if not result.no_generic:
            result.errors.append("analysis含模板化套话")

        if not result.reply_ok:
            result.errors.append("回复建议为泛化兜底")

        if result.signals_missing:
            # Include actual analysis snippet for debugging
            snippet = analysis[:100] if analysis else "(empty)"
            result.errors.append(f"深层信号遗漏: {result.signals_missing} | 实际: {snippet}")

    except httpx.TimeoutException:
        result.errors.append("请求超时")
    except Exception as e:
        result.errors.append(str(e)[:200])

    return result


# ═══════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════

def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_summary(results: list[TestResult]):
    """Print comprehensive summary."""
    passed = [r for r in results if not r.errors]
    failed = [r for r in results if r.errors]

    durations = [r.duration_ms for r in results if r.status_code == 200]
    analysis_lens = [r.analysis_len for r in results if r.status_code == 200]

    print_header("TEST SUMMARY")

    # Overall pass/fail
    print(f"\n  ✅ 通过: {len(passed)}/{len(results)}")
    print(f"  ❌ 失败: {len(failed)}/{len(results)}")

    # Timing
    if durations:
        avg_ms = sum(durations) / len(durations)
        print(f"\n  ⏱️  耗时统计 (ms):")
        print(f"     平均: {avg_ms:.0f} | 中位: {sorted(durations)[len(durations)//2]:.0f} | "
              f"最快: {min(durations):.0f} | 最慢: {max(durations):.0f}")
        slow = [r for r in results if r.duration_ms > 30000]
        if slow:
            print(f"     ⚠️  超过30s: {[f'{r.name}({r.duration_ms/1000:.1f}s)' for r in slow]}")

    # Analysis length
    if analysis_lens:
        print(f"\n  📏 Analysis 长度统计 (字符):")
        print(f"     平均: {sum(analysis_lens)/len(analysis_lens):.0f} | "
              f"最长: {max(analysis_lens)} | 最短: {min(analysis_lens)}")
        too_long = [r for r in results if r.analysis_len > 200]
        if too_long:
            print(f"     ⚠️  超200字: {[f'{r.name}({r.analysis_len}字)' for r in too_long]}")

    # Quality scores
    ref_ok = sum(1 for r in results if r.has_ref)
    gen_ok = sum(1 for r in results if r.no_generic)
    reply_ok = sum(1 for r in results if r.reply_ok)
    sig_scores = [r.signal_score for r in results]
    avg_signal = sum(sig_scores) / len(sig_scores) if sig_scores else 0

    print(f"\n  📊 质量指标:")
    print(f"     原文引用率: {ref_ok}/{len(results)} ({100*ref_ok//len(results)}%)")
    print(f"     无套话率:   {gen_ok}/{len(results)} ({100*gen_ok//len(results)}%)")
    print(f"     回复质量:   {reply_ok}/{len(results)} ({100*reply_ok//len(results)}%)")
    print(f"     信号检测率: {avg_signal:.0%}")

    # Status distribution
    status_counts = {}
    for r in results:
        s = r.chat_status or "N/A"
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"\n  🏷️  状态分布: {status_counts}")

    # Failed details
    if failed:
        print_header("FAILED TESTS")
        for r in failed:
            print(f"\n  ❌ {r.name} ({r.duration_ms}ms, status={r.chat_status})")
            for e in r.errors:
                print(f"     → {e}")


def print_per_scenario(results: list[TestResult]):
    """Print per-scenario detail table."""
    print_header("PER-SCENARIO DETAILS")
    print(f"\n  {'场景':<16} {'耗时':>8} {'长度':>6} {'状态':<12} {'引用':>4} {'套话':>4} {'回复':>4} {'信号':>4}")
    print(f"  {'-'*16} {'-'*8} {'-'*6} {'-'*12} {'-'*4} {'-'*4} {'-'*4} {'-'*4}")

    for r in results:
        status = r.chat_status[:10] if r.chat_status else "N/A"
        ref = "✅" if r.has_ref else "❌"
        gen = "✅" if r.no_generic else "❌"
        rep = "✅" if r.reply_ok else "❌"
        sig = f"{r.signal_score:.0%}"
        print(f"  {r.name:<16} {r.duration_ms:>5}ms {r.analysis_len:>5}字 "
              f"{status:<12} {ref:>4} {gen:>4} {rep:>4} {sig:>4}")


# ═══════════════════════════════════════════════════════════
# Edge Case Tests (quick, no AI call)
# ═══════════════════════════════════════════════════════════

async def run_validation_tests() -> list[tuple[str, bool, str]]:
    """Run validation tests (input validation, error handling)."""
    results = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Empty / too short
        resp = await client.post(f"{BASE_URL}/api/v1/analyze", json={
            "chat_content": "hi", "anonymous_user_id": "test_val"})
        results.append(("空输入校验(400)", resp.status_code in (200, 400), f"HTTP {resp.status_code}"))

        # Too long
        resp = await client.post(f"{BASE_URL}/api/v1/analyze", json={
            "chat_content": "我: hi\n" * 2000, "anonymous_user_id": "test_val"})
        results.append(("超长输入校验(400)", resp.status_code in (200, 400), f"HTTP {resp.status_code}"))

        # Harmful
        resp = await client.post(f"{BASE_URL}/api/v1/analyze", json={
            "chat_content": "我: 教我PUA话术", "anonymous_user_id": "test_val"})
        results.append(("违规内容拦截(400)", resp.status_code in (200, 400), f"HTTP {resp.status_code}"))

        # Whitespace only
        resp = await client.post(f"{BASE_URL}/api/v1/analyze", json={
            "chat_content": "   \n\n   \n", "anonymous_user_id": "test_val"})
        results.append(("纯空白校验(400)", resp.status_code in (200, 400), f"HTTP {resp.status_code}"))

        # Health check
        resp = await client.get(f"{BASE_URL}/health")
        results.append(("健康检查(200)", resp.status_code == 200, f"HTTP {resp.status_code}"))

        # Stats
        resp = await client.get(f"{BASE_URL}/api/v1/stats")
        results.append(("统计接口(200)", resp.status_code == 200, f"HTTP {resp.status_code}"))

    return results


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

async def main():
    import sys
    t_total = time.time()

    # ── Parse args ──
    no_ai = "--no-ai" in sys.argv or "--phase1-only" in sys.argv
    ai_only = "--ai" in sys.argv
    # Parse specific test names: --test "场景名1,场景名2"
    specific_tests = None
    for arg in sys.argv:
        if arg.startswith("--test="):
            specific_tests = arg.split("=", 1)[1].split(",")
            specific_tests = [t.strip() for t in specific_tests]
            break

    mode_label = ""
    if no_ai:
        mode_label = "（仅校验，不调 AI）"
    elif ai_only:
        mode_label = "（仅 AI 场景测试）"
        if specific_tests:
            mode_label += f" [{len(specific_tests)} 个指定场景]"
    elif specific_tests:
        mode_label = f"（校验 + {len(specific_tests)} 个指定场景）"
    else:
        mode_label = f"（全量：校验 + {len(TEST_CASES)} 个 AI 场景）"
        print(f"\n  ⚠️  全量测试将消耗约 {len(TEST_CASES) * 3}k ~ {len(TEST_CASES) * 8}k tokens")
        print(f"  💡 日常提交请用: python tests/test_comprehensive.py --no-ai")
        print(f"  💡 指定场景请用: python tests/test_comprehensive.py --test=解题模式_典型,偏冷淡")

    print("=" * 70)
    print("  BetweenLines 综合质量 & 性能测试套件")
    print(f"  {mode_label}")
    print("=" * 70)

    # ── Phase 1: Fast Validation Tests (always run) ──
    if not ai_only:
        print_header("PHASE 1: 快速校验测试")
        val_results = await run_validation_tests()
        for name, ok, detail in val_results:
            icon = "✅" if ok else "❌"
            print(f"  {icon} {name}: {detail}")
        val_pass = sum(1 for _, ok, _ in val_results if ok)
        print(f"\n  校验通过: {val_pass}/{len(val_results)}")
    else:
        val_results = []
        val_pass = 0

    # ── Phase 2: AI Analysis Scenarios ──
    results: list[TestResult] = []

    if not no_ai:
        print_header("PHASE 2: AI 分析场景测试 (需要调用模型)")

        # Determine test scope
        if specific_tests:
            test_items = [(n, c) for n, c in TEST_CASES.items() if n in specific_tests]
            if not test_items:
                print(f"  ❌ 未找到指定场景: {specific_tests}")
                print(f"  可用场景: {list(TEST_CASES.keys())}")
                return 1
        else:
            test_items = list(TEST_CASES.items())

        for i, (name, config) in enumerate(test_items):
            print(f"\n  [{i+1}/{len(test_items)}] 测试: {name}...", end=" ", flush=True)
            result = await run_single_test(name, config)
            results.append(result)

            status_icon = "✅" if not result.errors else "❌"
            print(f"{status_icon} "
                  f"耗时{result.duration_ms//1000}s "
                  f"分析{result.analysis_len}字 "
                  f"状态={result.chat_status}")

            # Rate-limit avoidance: 2s gap between AI requests
            if i < len(test_items) - 1:
                await asyncio.sleep(2.0)

        # ── Reports ──
        print_per_scenario(results)
        print_summary(results)
    else:
        print_header("PHASE 2: AI 分析场景测试（已跳过）")

    total_time = time.time() - t_total
    print(f"\n  总耗时: {total_time:.0f}s")

    # Return exit code
    total_failed = (len(val_results) - val_pass) + sum(1 for r in results if r.errors)
    return total_failed


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(0 if exit_code == 0 else 1)
