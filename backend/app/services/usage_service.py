"""Usage tracking service for anonymous users.

Uses anonymous_user_id from client (localStorage) instead of IP-based tracking.
Daily quotas auto-reset based on date — no cron jobs needed.
"""
import hashlib
import logging
from datetime import datetime, timezone
from app.core.config import settings
from app.services.storage import get_daily_usage, increment_daily_usage

logger = logging.getLogger(__name__)

VALID_RELATIONSHIP_TYPES = {"romantic", "friend", "family", "coworker", "other"}


def _get_total_reward_count(anonymous_user_id: str) -> int:
    """Get today's total reward bonus (share + feedback)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0
    if settings.ENABLE_SHARE_REWARD:
        from app.services.storage import get_share_reward_count
        share = get_share_reward_count(anonymous_user_id, today)
        total += min(share, settings.MAX_SHARE_REWARDS_PER_DAY)
    if settings.ENABLE_FEEDBACK_REWARD:
        from app.services.storage import get_feedback_reward_count
        fb = get_feedback_reward_count(anonymous_user_id, today)
        total += min(fb, settings.MAX_FEEDBACK_REWARDS_PER_DAY)
    return total


def check_and_increment_usage(anonymous_user_id: str, usage_type: str) -> dict:
    """Check if user has remaining quota (base + reward), increment if allowed.

    Args:
        anonymous_user_id: Client-generated anonymous ID (e.g. cc_8a4f21d3)
        usage_type: "analysis" or "screenshot" (both count against unified analysis quota)

    Returns:
        {"allowed": bool, "used": int, "limit": int, "detail": str | None}
    """
    usage = get_daily_usage(anonymous_user_id)

    # V2: unified quota — text and image analysis share the same daily limit
    used = usage["analysis_count"]
    base_limit = settings.FREE_DAILY_LIMIT
    effective_limit = base_limit + _get_total_reward_count(anonymous_user_id)

    if used >= effective_limit:
        return {
            "allowed": False,
            "used": used,
            "limit": effective_limit,
            "detail": "daily_limit_reached",
        }

    # Increment usage (always increments text_analysis_count for unified quota)
    try:
        new_count = increment_daily_usage(anonymous_user_id, "analysis")
    except Exception as e:
        logger.warning(f"Failed to increment usage: {e}")
        new_count = used + 1

    return {
        "allowed": True,
        "used": new_count,
        "limit": effective_limit,
        "detail": None,
    }


def get_usage_info(anonymous_user_id: str) -> dict:
    """Get usage info for a user (V2: unified quota — all analysis types share one limit)."""
    usage = get_daily_usage(anonymous_user_id)

    # Separate counts for frontend display
    from app.services.storage import get_share_reward_count, get_feedback_reward_count
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    share_reward_count = get_share_reward_count(anonymous_user_id, today) if settings.ENABLE_SHARE_REWARD else 0
    fb_reward_count = get_feedback_reward_count(anonymous_user_id, today) if settings.ENABLE_FEEDBACK_REWARD else 0
    total_reward = _get_total_reward_count(anonymous_user_id)

    return {
        "analysis_used": usage["analysis_count"],
        "analysis_limit": settings.FREE_DAILY_LIMIT,
        "analysis_reward": total_reward,
        "screenshot_used": usage["analysis_count"],
        "screenshot_limit": settings.FREE_DAILY_LIMIT,
        "max_chat_length": settings.MAX_CHAT_LENGTH,
        "max_screenshots_per_request": settings.MAX_SCREENSHOTS_PER_REQUEST,
        "share_reward_enabled": settings.ENABLE_SHARE_REWARD,
        "max_share_rewards_per_day": settings.MAX_SHARE_REWARDS_PER_DAY,
        "share_rewards_used_today": share_reward_count,
        "feedback_reward_enabled": settings.ENABLE_FEEDBACK_REWARD,
        "max_feedback_rewards_per_day": settings.MAX_FEEDBACK_REWARDS_PER_DAY,
        "feedback_rewards_used_today": fb_reward_count,
    }


def grant_share_reward(anonymous_user_id: str, share_type: str, share_hash: str) -> dict:
    """Grant a share reward (bonus analysis count) if eligible.

    Returns:
        {"granted": bool, "bonus_count": int, "message": str}
    """
    if not settings.ENABLE_SHARE_REWARD:
        return {"granted": False, "bonus_count": 0, "message": "Share reward is not enabled"}

    from app.services.storage import save_share_reward, get_share_reward_count

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Check daily limit
    current_rewards = get_share_reward_count(anonymous_user_id, today)
    if current_rewards >= settings.MAX_SHARE_REWARDS_PER_DAY:
        return {"granted": False, "bonus_count": 0, "message": "Daily share reward limit reached"}

    # Check dedup by share_hash
    from app.services.storage import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        existing = cursor.execute(
            "SELECT id FROM share_rewards WHERE anonymous_user_id = ? AND reward_date = ? AND share_hash = ?",
            (anonymous_user_id, today, share_hash),
        ).fetchone()
        if existing:
            return {"granted": False, "bonus_count": 0, "message": "Already rewarded for this share"}

    # Grant reward
    reward_id = save_share_reward(anonymous_user_id, share_type, share_hash)

    return {"granted": True, "bonus_count": 1, "message": "Bonus analysis granted!"}
