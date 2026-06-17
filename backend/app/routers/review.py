"""Post-Reply Review router — analyze follow-up conversations."""

import time
import json
import logging
from fastapi import APIRouter, HTTPException, Depends

from app.schemas.chat import ReviewRequest, ReviewResponse, ConversationChanges
from app.services.review_service import ReviewService
from app.services.storage import get_analysis_log, save_review_log
from app.services.doubao_service import DoubaoService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["review"])


# Minimum new chat length for meaningful review
MIN_REVIEW_CHAT_LENGTH = 10


def _extract_features(chat_content: str) -> dict:
    """Extract features from chat content for comparison."""
    ds = DoubaoService()
    return ds._extract_chat_features(chat_content)


@router.post("/review", response_model=ReviewResponse)
async def review_chat(
    request_body: ReviewRequest,
    service: ReviewService = Depends(lambda: ReviewService()),
):
    """复盘分析——将后续聊天与上次分析对比，评估建议有效性和关系变化。

    要求提供上次分析的 analysis_id 和新的聊天内容。
    """
    # ── Validate length ──
    new_len = len(request_body.new_chat_content.strip())
    if new_len < MIN_REVIEW_CHAT_LENGTH:
        logger.info(f"Review skipped: new chat too short ({new_len} chars)")
        return ReviewResponse(
            review_status="insufficient_data",
            changes=ConversationChanges(),
            previous_advice_effectiveness="cannot_tell",
            summary="后续聊天数据不足，无法进行有效复盘。建议积累更多对话后再来对比。" if request_body.language == "zh" else "Not enough follow-up data for a meaningful review. Try again with more conversation messages.",
            next_step_advice="请在有了更多聊天内容后再回来复盘。" if request_body.language == "zh" else "Come back for a review after more conversation exchanges.",
        )

    # ── Look up previous analysis ──
    prev_log = get_analysis_log(request_body.analysis_id)
    if prev_log is None:
        raise HTTPException(
            status_code=404,
            detail=f"分析记录 {request_body.analysis_id} 未找到。请确保 analysis_id 正确。",
        )

    # ── Extract features from previous analysis ──
    prev_features_raw = prev_log.get("features_json")
    if not prev_features_raw:
        raise HTTPException(
            status_code=404,
            detail=f"分析记录 {request_body.analysis_id} 缺少特征数据，无法进行对比复盘。",
        )
    try:
        previous_features = json.loads(prev_features_raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="分析记录特征数据损坏，无法进行对比复盘。",
        )

    # ── Run AI comparison ──
    try:
        result = await service.compare_chat(
            previous_features=previous_features,
            new_chat_content=request_body.new_chat_content,
            relationship_type=request_body.relationship_type,
            language=request_body.language or "zh",
        )
    except Exception as e:
        logger.error(f"Review comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="复盘分析失败，请稍后重试。",
        )

    # ── Save review log ──
    try:
        review_id = save_review_log(
            analysis_id=str(request_body.analysis_id),
            review_status=result.review_status,
            advice_effective=result.previous_advice_effectiveness,
            new_chat_length=len(request_body.new_chat_content),
        )
        result.review_id = review_id
    except Exception as log_error:
        logger.warning(f"Failed to save review log: {log_error}")

    return result
