"""
Unit tests for enhanced analysis quality features.

Tests: feature extraction, quality validation, parse response.
No API calls required — pure logic tests.
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.doubao_service import DoubaoService
from app.schemas.chat import ChatAnalysisResponse, ChatStatus


# ── Fixtures ──

@pytest.fixture
def service():
    """Create DoubaoService instance (no API key needed for logic tests)."""
    return DoubaoService.__new__(DoubaoService)


# ═══════════════════════════════════════════════════════════════
# 1. Enhanced Feature Extraction Tests
# ═══════════════════════════════════════════════════════════════

class TestFeatureExtraction:
    """Test _extract_chat_features with enhanced fields."""

    def test_basic_fields_still_present(self, service):
        chat = "我: 你好\n他: 你好呀"
        features = service._extract_chat_features(chat)
        assert features["total_messages"] == 2
        assert features["user_msgs"] == 1
        assert features["other_msgs"] == 1
        assert "notable_patterns" in features

    def test_new_emoji_fields_exist(self, service):
        chat = "我: 你好\n他: 好的😊"
        features = service._extract_chat_features(chat)
        assert "other_emoji_count" in features
        assert "user_emoji_count" in features
        assert "other_short_ratio" in features
        assert "sentiment_pos" in features
        assert "sentiment_neg" in features
        assert "topic_coherence" in features

    def test_emoji_detection_unicode(self, service):
        """Test unicode emoji detection."""
        chat = "他: 好的😊\n他: 哈哈😂\n我: 嗯嗯"
        features = service._extract_chat_features(chat)
        assert features["other_emoji_count"] >= 2  # 😊 and 😂

    def test_emoji_detection_bracket(self, service):
        """Test Chinese bracket emoji [笑哭] detection."""
        chat = "他: 好的[笑哭]\n他: [捂脸]是的\n我: ok"
        features = service._extract_chat_features(chat)
        assert features["other_emoji_count"] >= 2

    def test_short_reply_ratio(self, service):
        """Test short reply ratio (≤3 chars after stripping prefix)."""
        chat = (
            "他: 嗯\n"
            "他: 好的\n"
            "他: 今天天气真不错啊\n"
            "我: 是呀"
        )
        features = service._extract_chat_features(chat)
        # "嗯"(1) and "好的"(2) are short, "今天天气真不错啊"(8) is not
        # So 2 out of 3 = ~66.7%
        assert features["other_short_ratio"] == pytest.approx(66.7, abs=0.1)

    def test_sentiment_positive_detection(self, service):
        """Test positive sentiment word detection."""
        chat = (
            "他: 哈哈好呀\n"
            "他: 太棒了\n"
            "他: 随便\n"
            "我: ok"
        )
        features = service._extract_chat_features(chat)
        # "好呀"→positive, "太棒了" doesn't match exactly but "棒" does
        assert features["sentiment_pos"] >= 1

    def test_sentiment_negative_detection(self, service):
        """Test negative sentiment word detection."""
        chat = (
            "他: 嗯\n"
            "他: 随便\n"
            "他: 知道了\n"
            "我: ok"
        )
        features = service._extract_chat_features(chat)
        # "嗯", "随便", "知道了" → 3 negatives
        assert features["sentiment_neg"] >= 2

    def test_topic_coherence_detection(self, service):
        """Test topic coherence detection (references to prior topics)."""
        chat = (
            "我: 周末去爬山怎么样\n"
            "他: 刚才你说的爬山，我觉得可以\n"
            "他: 上次我们去的地方也不错\n"
            "我: 好的"
        )
        features = service._extract_chat_features(chat)
        # "刚才" and "上次" are topic references
        assert features["topic_coherence"] >= 50.0

    def test_pattern_emoji_rich(self, service):
        """Test pattern detection for emoji-rich conversations."""
        chat = (
            "他: 好的😊\n"
            "他: 哈哈[笑哭]\n"
            "我: ok"
        )
        features = service._extract_chat_features(chat)
        patterns = features["notable_patterns"]
        assert "表情" in patterns or "emoji" in patterns.lower()

    def test_pattern_short_reply_signal(self, service):
        """Test pattern detection for short reply signals."""
        chat = (
            "他: 嗯\n"
            "他: 哦\n"
            "他: 好\n"
            "我: 你好"
        )
        features = service._extract_chat_features(chat)
        patterns = features["notable_patterns"]
        assert "敷衍" in patterns or "短" in patterns or "short" in patterns.lower()

    def test_pattern_sentiment_positive(self, service):
        """Test pattern detection for positive sentiment."""
        chat = (
            "他: 好呀好呀\n"
            "他: 哈哈开心\n"
            "我: ok"
        )
        features = service._extract_chat_features(chat)
        patterns = features["notable_patterns"]
        assert "积极" in patterns or "正面" in patterns or "好" in patterns

    def test_no_emoji_chat(self, service):
        """Test that emoji count is zero when no emojis present."""
        chat = "他: 你好\n我: 你好"
        features = service._extract_chat_features(chat)
        assert features["other_emoji_count"] == 0
        assert features["user_emoji_count"] == 0

    def test_single_message_edge_case(self, service):
        """Test edge case: single message won't crash."""
        chat = "我: 你好"
        features = service._extract_chat_features(chat)
        assert features["total_messages"] == 1
        assert features["other_emoji_count"] == 0
        assert features["other_short_ratio"] == 0


# ═══════════════════════════════════════════════════════════════
# 2. Quality Check Tests
# ═══════════════════════════════════════════════════════════════

class TestQualityCheck:
    """Test _check_analysis_quality method."""

    def test_good_quality_passes(self, service):
        """Test that a well-written analysis passes all checks."""
        data = {
            "chat_status": "偏冷淡",
            "analysis": '1.对方连续3条回复极短（"嗯""哦""好"），属于明显的敷衍模式。'
                        '2.用户连续追问3次，对方均未延伸话题。',
            "issues": ["对方回复过短", "用户追问过密"],
            "risks": ["可能产生厌烦感"],
            "reply_suggestions": {
                "natural": "那你先忙，有空再聊",
                "humorous": "看来今天不在状态哈哈",
                "mature": "了解，不打扰你了",
            },
            "timing_advice": "建议暂停追问，等对方主动开启话题",
        }
        warnings = service._check_analysis_quality(data, "zh")
        # Should have few or no warnings for good quality
        # (may have warning about "specific references" since no digit+条 pattern)
        # but at least should NOT have generic phrase / fallback / vague warnings
        for w in warnings:
            assert "Generic phrase" not in w
            assert "generic fallback" not in w
            assert "Vague timing" not in w

    def test_generic_phrase_detected(self, service):
        """Test that generic cliché phrases are flagged."""
        data = {
            "chat_status": "普通互动",
            "analysis": "祝你们越来越好，保持当前的良好互动状态。",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "可以自然地继续聊天。",
                "humorous": "用轻松的方式回应。",
                "mature": "保持稳重得体的交流。",
            },
            "timing_advice": "保持节奏即可。",
        }
        warnings = service._check_analysis_quality(data, "zh")
        assert len(warnings) >= 3  # generic phrase + fallback suggestions + vague timing

    def test_fallback_reply_suggestions_detected(self, service):
        """Test that exact fallback suggestions are flagged."""
        data = {
            "chat_status": "普通互动",
            "analysis": "对方回复正常，互动尚可。",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "可以自然地继续聊天。",
                "humorous": "自定义回复内容...",
                "mature": "保持稳重得体的交流。",
            },
            "timing_advice": "保持当前节奏。",
        }
        warnings = service._check_analysis_quality(data, "zh")
        fallback_warnings = [w for w in warnings if "fallback" in w]
        # natural and mature match fallback, humorous does not
        assert len(fallback_warnings) == 2

    def test_vague_timing_detected(self, service):
        """Test that vague timing advice is flagged."""
        data = {
            "chat_status": "普通互动",
            "analysis": "互动正常，可以继续。",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "好的，收到",
                "humorous": "哈哈好",
                "mature": "了解，继续",
            },
            "timing_advice": "顺其自然吧，看情况。",
        }
        warnings = service._check_analysis_quality(data, "zh")
        vague_warnings = [w for w in warnings if "Vague timing" in w]
        assert len(vague_warnings) >= 1

    def test_lack_of_references_detected(self, service):
        """Test that analysis without specific references is flagged."""
        data = {
            "chat_status": "偏冷淡",
            "analysis": "对方不太积极，可能正在忙或者对这个话题不太感兴趣。建议换个话题。",
            "issues": ["对方兴趣不高"],
            "risks": [],
            "reply_suggestions": {
                "natural": "那你先忙",
                "humorous": "哈哈好吧",
                "mature": "好的，有空再聊",
            },
            "timing_advice": "换个话题方向",
        }
        warnings = service._check_analysis_quality(data, "zh")
        ref_warnings = [w for w in warnings if "specific text references" in w.lower()]
        assert len(ref_warnings) >= 1

    def test_analysis_with_quotes_passes(self, service):
        """Test that analysis using quotes is recognized as having references."""
        data = {
            "chat_status": "偏冷淡",
            "analysis": '对方回复"嗯""哦"，明显的敷衍。',
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "那先这样",
                "humorous": "今天没电了哈哈",
                "mature": "好的，有空聊",
            },
            "timing_advice": "暂停追问",
        }
        warnings = service._check_analysis_quality(data, "zh")
        ref_warnings = [w for w in warnings if "specific text references" in w.lower()]
        # Has quotes → should NOT have reference warning
        assert len(ref_warnings) == 0

    def test_english_fallback_detection(self, service):
        """Test English fallback suggestions are detected."""
        data = {
            "chat_status": "normal",
            "analysis": "The conversation seems fine.",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "Keep the conversation going naturally.",
                "humorous": "Respond in a light-hearted way.",
                "mature": "Maintain a composed and respectful tone.",
            },
            "timing_advice": "Keep the current pace.",
        }
        warnings = service._check_analysis_quality(data, "en")
        assert len(warnings) >= 3

    def test_empty_warnings_for_analysis_as_list(self, service):
        """Test that analysis provided as list is handled gracefully."""
        data = {
            "chat_status": "偏冷淡",
            "analysis": ['对方说"嗯"', '用户追问过多'],
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "那先这样",
                "humorous": "好的哈哈",
                "mature": "有空再聊",
            },
            "timing_advice": "暂停追问",
        }
        warnings = service._check_analysis_quality(data, "zh")
        # Should not crash, analysis as list converted to string
        assert isinstance(warnings, list)

    def test_quality_check_non_blocking(self, service):
        """Test that quality check never raises exceptions with malformed data."""
        # Empty data
        warnings = service._check_analysis_quality({}, "zh")
        assert isinstance(warnings, list)
        # None values
        data = {"analysis": None, "reply_suggestions": {}, "timing_advice": None}
        warnings = service._check_analysis_quality(data, "zh")
        assert isinstance(warnings, list)


# ═══════════════════════════════════════════════════════════════
# 3. Parse Response Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestParseResponse:
    """Test _parse_response with quality check integration."""

    VALID_JSON_ZH = json.dumps({
        "chat_status": "积极互动",
        "analysis": '对方主动分享日常（"好累"），并回应了用户的关心。互动质量良好。',
        "issues": [],
        "risks": [],
        "reply_suggestions": {
            "natural": "辛苦了，早点休息",
            "humorous": "打工人打工魂哈哈",
            "mature": "注意身体，别太拼",
        },
        "timing_advice": "现在可以继续聊，氛围不错",
    })

    def test_parse_valid_json(self, service):
        """Test that valid JSON parses correctly and quality check runs."""
        result = service._parse_response(self.VALID_JSON_ZH, "zh")
        assert isinstance(result, ChatAnalysisResponse)
        assert result.chat_status == ChatStatus.POSITIVE
        assert "辛苦了" in result.reply_suggestions.natural
        assert len(result.issues) == 0
        assert len(result.risks) == 0

    def test_parse_with_markdown_wrapper(self, service):
        """Test JSON wrapped in markdown code blocks."""
        wrapped = f"```json\n{self.VALID_JSON_ZH}\n```"
        result = service._parse_response(wrapped, "zh")
        assert isinstance(result, ChatAnalysisResponse)
        assert result.chat_status == ChatStatus.POSITIVE

    def test_parse_with_unknown_status_defaults(self, service):
        """Test that unknown chat_status defaults to NORMAL."""
        data = json.dumps({
            "chat_status": "some_unknown_status",
            "analysis": "test",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "test reply",
                "humorous": "test reply",
                "mature": "test reply",
            },
            "timing_advice": "test",
        })
        result = service._parse_response(data, "zh")
        assert result.chat_status == ChatStatus.NORMAL

    def test_parse_with_analysis_as_list(self, service):
        """Test that analysis as list is coerced to string."""
        data = json.dumps({
            "chat_status": "普通互动",
            "analysis": ["point 1", "point 2", "point 3"],
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "test",
                "humorous": "test",
                "mature": "test",
            },
            "timing_advice": "test",
        })
        result = service._parse_response(data, "zh")
        assert isinstance(result.analysis, str)
        assert "point 1" in result.analysis

    def test_parse_with_missing_fields_has_defaults(self, service):
        """Test that missing fields get sensible defaults."""
        data = json.dumps({
            "chat_status": "普通互动",
            "analysis": "test analysis",
        })
        result = service._parse_response(data, "zh")
        assert result.issues == []
        assert result.risks == []
        assert "继续聊天" in result.reply_suggestions.natural
        assert "保持当前节奏" in result.timing_advice

    def test_parse_response_handles_cold_status(self, service):
        """Test COLD status mapping."""
        data = json.dumps({
            "chat_status": "偏冷淡",
            "analysis": "test",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "test", "humorous": "test", "mature": "test",
            },
            "timing_advice": "test",
        })
        result = service._parse_response(data, "zh")
        assert result.chat_status == ChatStatus.COLD

    def test_parse_response_handles_high_risk_status(self, service):
        """Test HIGH_RISK status mapping."""
        data = json.dumps({
            "chat_status": "对话风险较高",
            "analysis": "test",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "test", "humorous": "test", "mature": "test",
            },
            "timing_advice": "test",
        })
        result = service._parse_response(data, "zh")
        assert result.chat_status == ChatStatus.HIGH_RISK

    def test_parse_response_handles_polite_status(self, service):
        """Test POLITE status mapping."""
        data = json.dumps({
            "chat_status": "礼貌回应",
            "analysis": "test",
            "issues": [],
            "risks": [],
            "reply_suggestions": {
                "natural": "test", "humorous": "test", "mature": "test",
            },
            "timing_advice": "test",
        })
        result = service._parse_response(data, "zh")
        assert result.chat_status == ChatStatus.POLITE

    def test_invalid_json_raises(self, service):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError):
            service._parse_response("not json at all", "zh")


# ═══════════════════════════════════════════════════════════════
# 4. Config Validation Tests
# ═══════════════════════════════════════════════════════════════

class TestConfig:
    """Test that config changes are applied correctly."""

    def test_max_tokens_sufficient(self):
        """Verify MAX_TOKENS >= 800 for sufficient output space."""
        from app.core.config import settings
        assert settings.MAX_TOKENS >= 800, (
            f"MAX_TOKENS should be >= 800 for sufficient output space, got {settings.MAX_TOKENS}"
        )

    def test_temperature_optimal(self):
        """Verify TEMPERATURE is in optimal range 0.4-0.6."""
        from app.core.config import settings
        assert 0.4 <= settings.TEMPERATURE <= 0.6, (
            f"TEMPERATURE should be 0.4-0.6 for balanced output, got {settings.TEMPERATURE}"
        )
