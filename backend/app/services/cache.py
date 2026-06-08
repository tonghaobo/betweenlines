"""Simple in-memory content-hash cache to prevent re-analyzing the same content.

Avoids wasting AI API calls when user refreshes and re-submits the same chat.
"""

import hashlib
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# {content_hash: (ChatAnalysisResponse, expire_time)}
_cache: dict[str, tuple] = {}

# TTL for cached results (10 minutes)
CACHE_TTL_SECONDS = 10 * 60


def _make_hash(content: str, user_id: str, relationship_type: str) -> str:
    """Generate a deterministic hash for chat content + user."""
    raw = f"{user_id}:{relationship_type}:{content}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_result(content: str, user_id: str, relationship_type: str) -> Optional[dict]:
    """Return cached analysis result if valid, otherwise None."""
    key = _make_hash(content, user_id, relationship_type)
    entry = _cache.get(key)
    if entry is None:
        return None
    result, expire_at = entry
    if time.time() > expire_at:
        del _cache[key]
        return None
    logger.info(f"Cache hit for {user_id[:12]}... (hash={key[:8]}...)")
    return result


def set_cached_result(content: str, user_id: str, relationship_type: str, result: dict):
    """Store analysis result in cache."""
    key = _make_hash(content, user_id, relationship_type)
    expire_at = time.time() + CACHE_TTL_SECONDS
    _cache[key] = (result, expire_at)

    # Cleanup expired entries when cache grows too large
    if len(_cache) > 100:
        _cleanup()


def _cleanup():
    """Remove expired cache entries."""
    now = time.time()
    expired = [k for k, (_, exp) in _cache.items() if now > exp]
    for k in expired:
        del _cache[k]
    if expired:
        logger.info(f"Cache cleanup: removed {len(expired)} expired entries")
