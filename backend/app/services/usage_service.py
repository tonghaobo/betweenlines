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


def _get_reward_count(anonymous_user_id: str) -> int:
    """Get today's share reward count (bonus analysis quota)."""
    if not settings.ENABLE_SHARE_REWARD:
        return 0
    from app.services.storage import get_share_reward_count
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return get_share_reward_count(anonymous_user_id, today)


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
    reward_count = _get_reward_count(anonymous_user_id)
    effective_limit = base_limit + min(reward_count, settings.MAX_SHARE_REWARDS_PER_DAY)

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
    reward_count = _get_reward_count(anonymous_user_id)
    reward = min(reward_count, settings.MAX_SHARE_REWARDS_PER_DAY) if settings.ENABLE_SHARE_REWARD else 0
    return {
        "analysis_used": usage["analysis_count"],
        "analysis_limit": settings.FREE_DAILY_LIMIT,
        "analysis_reward": reward,
        "screenshot_used": usage["analysis_count"],  # V2: same bucket
        "screenshot_limit": settings.FREE_DAILY_LIMIT,  # V2: same limit
        "max_chat_length": settings.MAX_CHAT_LENGTH,
        "max_screenshots_per_request": settings.MAX_SCREENSHOTS_PER_REQUEST,
        "share_reward_enabled": settings.ENABLE_SHARE_REWARD,
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
    with get_daily_usage(anonymous_user_id).__class__.__mro__[0]:  # no-op, just ensuring import
        pass

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
