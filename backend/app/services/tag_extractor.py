"""Rule-based tag extraction for chat analysis results.

Phase 3: Auto-label generation using features and analysis text.
Hybrid approach: rule layer (zero-cost) first, AI supplement when confidence is low.

Tags extracted:
  - conversation_stage: 初识/熟悉/暧昧/拉扯/冷淡
  - other_style: 热情型/礼貌型/高冷型/慢热型
  - user_issue: 查户口/太急/输出太多/幽默不足
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# ── Tag value sets ──

CONVERSATION_STAGES = ["初识", "熟悉", "暧昧", "拉扯", "冷淡"]
OTHER_STYLES = ["热情型", "礼貌型", "高冷型", "慢热型"]
USER_ISSUES = ["查户口", "太急", "输出太多", "幽默不足"]


# ── Stage keywords ──

STAGE_KEYWORDS = {
    "初识": ["刚认识", "第一次", "初次", "初识", "刚加", "新认识", "不熟", "还不了解"],
    "熟悉": ["经常聊", "老友", "老朋友", "很熟", "相处久了", "认识很久", "天天聊"],
    "暧昧": ["暧昧", "心动", "好感", "暗示", "试探", "撩", "有感觉", "喜欢他", "喜欢她", "有意思"],
    "拉扯": ["拉扯", "忽冷忽热", "若即若离", "推拉", "博弈", "忽近忽远", "不回消息", "已读不回"],
    "冷淡": ["冷淡", "敷衍", "不回", "已读", "冷漠", "爱答不理", "没兴趣", "疏远", "降温"],
}


def _match_stage_by_keywords(analysis_text: str, issues: list[str]) -> tuple[str, float]:
    """Match conversation_stage by keyword count in analysis text and issues.
    Returns (stage, confidence) where confidence is 0.0~1.0.
    """
    text = analysis_text + " " + " ".join(issues)
    scores: dict[str, int] = {}
    for stage, keywords in STAGE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[stage] = count

    if not scores:
        return ("", 0.0)

    best = max(scores, key=scores.get)
    max_count = scores[best]
    total_count = sum(scores.values())
    confidence = max_count / total_count if total_count > 0 else 0.0

    # Require at least 2 keyword hits or confidence > 0.5 for a valid match
    if max_count < 2 and confidence <= 0.5:
        return ("", 0.0)

    return (best, confidence)


# ── Style inference from features + status ──

STYLE_KEYWORDS = {
    "热情型": ["积极", "热情", "主动", "秒回", "话多", "表情包", "emoji多", "分享欲"],
    "礼貌型": ["礼貌", "客气", "谢谢", "不好意思", "客气回应", "有分寸"],
    "高冷型": ["高冷", "简短", "冷淡", "疏远", "少回复", "回复慢", "冷", "不主动"],
    "慢热型": ["慢热", "谨慎", "试探", "慢", "逐渐", "慢慢", "需要时间"],
}


def _infer_other_style(chat_status: str, features_json: str | None) -> tuple[str, float]:
    """Infer the other person's communication style from status and features.
    Returns (style, confidence).
    """
    features = {}
    if features_json:
        try:
            features = json.loads(features_json)
        except (json.JSONDecodeError, TypeError):
            pass

    scores: dict[str, int] = {}

    # Rule 1: status-based mapping
    status_map = {
        "积极互动": "热情型",
        "普通互动": "礼貌型",
        "礼貌回应": "礼貌型",
        "偏冷淡": "高冷型",
        "对话风险较高": "高冷型",
    }
    if chat_status in status_map:
        mapped = status_map[chat_status]
        scores[mapped] = scores.get(mapped, 0) + 3

    # Rule 2: feature-based
    other_short_ratio = features.get("other_short_ratio", 0)
    if other_short_ratio > 0.5:
        scores["高冷型"] = scores.get("高冷型", 0) + 2
    elif other_short_ratio < 0.2:
        scores["热情型"] = scores.get("热情型", 0) + 1

    other_question_ratio = features.get("other_question_ratio", 0)
    if other_question_ratio > 0.3:
        scores["热情型"] = scores.get("热情型", 0) + 2
    elif other_question_ratio < 0.1:
        scores["高冷型"] = scores.get("高冷型", 0) + 1

    other_emoji = features.get("other_emoji_count", 0)
    if other_emoji > 5:
        scores["热情型"] = scores.get("热情型", 0) + 2

    if not scores:
        return ("", 0.0)

    best = max(scores, key=scores.get)
    max_score = scores[best]
    total_score = sum(scores.values())
    confidence = max_score / total_score if total_score > 0 else 0.0

    # Require score >= 3 or confidence > 0.5
    if max_score < 3 and confidence <= 0.5:
        return ("", 0.0)

    return (best, confidence)


# ── User issue detection ──

ISSUE_KEYWORDS = {
    "查户口": ["查户口", "审问", "连续提问", "像面试", "太多问题", "盘问"],
    "太急": ["太急", "着急", "急", "太快", "焦虑", "push", "强迫", "催"],
    "输出太多": ["输出太多", "话太多", "大段", "长篇", "自说自话", "独角戏", "篇幅过长", "太长"],
    "幽默不足": ["幽默不足", "太严肃", "不够有趣", "缺乏幽默", "太正经", "无聊", "没意思", "干巴巴"],
}


def _detect_user_issues(analysis_text: str, issues: list[str]) -> tuple[str, float]:
    """Detect the primary user issue from analysis text and issues list.
    Returns (issue, confidence).
    """
    text = analysis_text + " " + " ".join(issues)
    scores: dict[str, int] = {}

    for issue, keywords in ISSUE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[issue] = count

    if not scores:
        return ("", 0.0)

    best = max(scores, key=scores.get)
    max_count = scores[best]
    total_count = sum(scores.values())
    confidence = max_count / total_count if total_count > 0 else 0.0

    if max_count < 2 and confidence <= 0.5:
        return ("", 0.0)

    return (best, confidence)


# ── Main extraction ──

CONFIDENCE_THRESHOLD = 0.6


def extract_tags(
    analysis_text: str,
    chat_status: str,
    issues: list[str],
    features_json: str | None = None,
) -> dict:
    """Extract all three tags using rule-based approach.

    Returns:
        {
            "conversation_stage": str,
            "other_style": str,
            "user_issue": str,
            "label_source": str,  # "rule" | "hybrid"
            "confidence": {
                "conversation_stage": float,
                "other_style": float,
                "user_issue": float,
            }
        }
    """
    stage, stage_conf = _match_stage_by_keywords(analysis_text, issues)
    style, style_conf = _infer_other_style(chat_status, features_json)
    issue, issue_conf = _detect_user_issues(analysis_text, issues)

    # Determine label source
    all_high_conf = all(c >= CONFIDENCE_THRESHOLD for c in [stage_conf, style_conf, issue_conf] if c > 0)
    source = "rule" if all_high_conf else "hybrid"

    result = {
        "conversation_stage": stage,
        "other_style": style,
        "user_issue": issue,
        "label_source": source,
        "confidence": {
            "conversation_stage": stage_conf,
            "other_style": style_conf,
            "user_issue": issue_conf,
        },
    }

    logger.info(
        f"Tags extracted: stage={stage}({stage_conf:.2f}), "
        f"style={style}({style_conf:.2f}), "
        f"issue={issue}({issue_conf:.2f}), "
        f"source={source}"
    )
    return result
