import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Query
from app.schemas.chat import (
    ChatAnalysisRequest,
    ChatAnalysisResponse,
    ScreenshotAnalysisResponse,
    FeedbackRequest,
    FeedbackResponse,
    OutcomeRequest,
    OutcomeResponse,
    TrackEventRequest,
    TrackEventResponse,
    MetricsResponse,
    UsageResponse,
    ShareRewardRequest,
    ShareRewardResponse,
)
from app.services.doubao_service import DoubaoService
from app.services.chat_cleaner import clean_chat_content, validate_chat_format, is_potentially_harmful
from app.services.usage_service import check_and_increment_usage, get_usage_info, grant_share_reward, VALID_RELATIONSHIP_TYPES
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


def get_doubao_service() -> DoubaoService:
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_doubao_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="Doubao API key not configured. Please set OPENAI_API_KEY in .env",
        )
    return DoubaoService()


@router.post("/analyze", response_model=ChatAnalysisResponse)
async def analyze_chat(
    request_body: ChatAnalysisRequest,
    service: DoubaoService = Depends(get_doubao_service),
):
    # ── Validate relationship type ──
    if request_body.relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relationship_type. Must be one of: {', '.join(VALID_RELATIONSHIP_TYPES)}",
        )

    # ── Daily usage check via anonymous_user_id ──
    usage_result = check_and_increment_usage(request_body.anonymous_user_id, "analysis")
    if not usage_result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="daily_limit_reached",
        )

    start_time = time.time()
    chat_length = len(request_body.chat_content)
    chat_status_result = None
    error_msg = None

    try:
        if len(request_body.chat_content.strip()) < settings.MIN_CHAT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Chat content must be at least {settings.MIN_CHAT_LENGTH} characters",
            )

        if len(request_body.chat_content) > settings.MAX_CHAT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Chat content must be at most {settings.MAX_CHAT_LENGTH} characters",
            )

        if is_potentially_harmful(request_body.chat_content):
            raise HTTPException(
                status_code=400,
                detail="内容包含不适当的请求。本工具仅用于正常社交沟通分析。",
            )

        cleaned_content = clean_chat_content(request_body.chat_content)
        warnings = validate_chat_format(cleaned_content)
        if warnings:
            logger.info(f"Chat format warnings: {warnings}")

        # Normalize chat structure (auto-parse participants, remove noise)
        from app.services.chat_normalizer import normalize_chat
        cleaned_content = normalize_chat(cleaned_content)

        result = await service.analyze_chat(cleaned_content, request_body.relationship_type, request_body.language or "zh")
        chat_status_result = result.chat_status.value

        return result

    except HTTPException:
        # Undo the usage increment on failure
        if not error_msg and usage_result["allowed"]:
            _undo_usage_increment(request_body.anonymous_user_id, "analysis")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Analysis error: {error_msg}", exc_info=True)
        # Undo usage increment on failure
        _undo_usage_increment(request_body.anonymous_user_id, "analysis")
        raise HTTPException(
            status_code=500,
            detail="分析失败，请稍后重试。",
        )
    finally:
        duration_ms = (time.time() - start_time) * 1000
        try:
            from app.services.storage import save_analysis_log
            save_analysis_log(
                chat_length=chat_length,
                chat_status=chat_status_result,
                duration_ms=duration_ms,
                error=error_msg,
                relationship_type=request_body.relationship_type,
            )
        except Exception as log_error:
            logger.warning(f"Failed to save analysis log: {log_error}")


def _undo_usage_increment(anonymous_user_id: str, usage_type: str):
    """Decrement usage count when analysis fails after increment."""
    try:
        from app.services.storage import decrement_daily_usage
        decrement_daily_usage(anonymous_user_id, usage_type)
    except Exception as e:
        logger.warning(f"Failed to undo usage increment: {e}")


@router.post("/analyze-screenshot", response_model=ScreenshotAnalysisResponse)
async def analyze_screenshot(
    anonymous_user_id: str = Query(..., min_length=3, max_length=64, description="客户端生成的匿名用户ID"),
    files: list[UploadFile] = File(...),
    service: DoubaoService = Depends(get_doubao_service),
):
    """上传聊天截图（支持多张），提取文字并返回供用户确认。
    
    Note: OCR extraction does NOT consume daily quota — only the final analysis step does.
    """
    # ── Validate file count ──
    if len(files) > settings.MAX_SCREENSHOTS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"单次最多上传 {settings.MAX_SCREENSHOTS_PER_REQUEST} 张截图，当前上传了 {len(files)} 张。",
        )

    start_time = time.time()

    # Validate each file
    for f in files:
        if f.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式：{f.content_type}。请上传 PNG、JPEG 或 WebP 格式的图片。",
            )

    # Read and validate each file
    file_data: list[tuple[bytes, str]] = []
    total_size = 0
    for f in files:
        image_bytes = await f.read()
        if len(image_bytes) > settings.MAX_SCREENSHOT_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"图片过大（{len(image_bytes) / 1024 / 1024:.1f}MB），请上传不超过 10MB 的图片。",
            )
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="上传的图片为空，请重新选择。")
        total_size += len(image_bytes)
        file_data.append((image_bytes, f.content_type))

    logger.info(f"Screenshot upload: {len(files)} file(s), total_size={total_size}")

    try:
        extracted_parts: list[str] = []
        for i, (image_bytes, content_type) in enumerate(file_data):
            text = await service.extract_text_from_screenshot(image_bytes, content_type)
            if text and len(text.strip()) >= 10:
                extracted_parts.append(text.strip())
            else:
                logger.warning(f"Screenshot {i + 1}: insufficient text extracted")

        if not extracted_parts:
            raise HTTPException(
                status_code=400,
                detail="未能从图片中提取到足够的聊天文字。请确保截图包含清晰的聊天消息。",
            )

        combined_text = "\n---\n".join(extracted_parts)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"Screenshot text extracted in {duration_ms:.0f}ms, length={len(combined_text)}")

        return ScreenshotAnalysisResponse(
            extracted_text=combined_text,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Screenshot analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="截图分析失败，请稍后重试。",
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    try:
        from app.services.storage import save_feedback
        save_feedback(
            request.helpful,
            request.analysis_id,
            ",".join(request.reason),
            request.comment,
        )
    except Exception as e:
        logger.warning(f"Failed to save feedback: {e}")

    return FeedbackResponse(message="感谢你的反馈！")


@router.post("/outcome", response_model=OutcomeResponse)
async def submit_outcome(request: OutcomeRequest):
    try:
        from app.services.storage import save_outcome
        save_outcome(request.analysis_id, request.reply_used, request.outcome)
    except Exception as e:
        logger.warning(f"Failed to save outcome: {e}")

    return OutcomeResponse(message="感谢你的反馈！")


@router.get("/stats")
async def get_stats():
    try:
        from app.services.storage import get_feedback_stats, get_outcome_stats
        feedback_stats = get_feedback_stats()
        outcome_stats = get_outcome_stats()
        return {**feedback_stats, **outcome_stats}
    except Exception as e:
        logger.warning(f"Failed to get stats: {e}")
        return {"error": "Stats unavailable"}


@router.post("/track", response_model=TrackEventResponse)
async def track_event(request: TrackEventRequest):
    """Record an analytics event. Non-blocking — errors are swallowed."""
    try:
        from app.services.storage import save_event, VALID_EVENTS
        if request.event_name not in VALID_EVENTS:
            logger.warning(f"Invalid event name: {request.event_name}")
            return TrackEventResponse(success=True)
        
        import json
        properties = json.dumps(request.properties) if request.properties else None
        save_event(
            anonymous_user_id=request.anonymous_user_id,
            event_name=request.event_name,
            properties=properties,
            session_id=request.session_id,
        )
    except Exception as e:
        logger.warning(f"Failed to save event: {e}")
    
    return TrackEventResponse(success=True)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get V1 analytics metrics."""
    try:
        from app.services.storage import get_metrics as compute_metrics
        return compute_metrics()
    except Exception as e:
        logger.warning(f"Failed to compute metrics: {e}")
        return MetricsResponse()


@router.get("/usage", response_model=UsageResponse)
async def get_usage(anonymous_user_id: str = Query(..., min_length=3, max_length=64)):
    """Get current user's daily usage info."""
    info = get_usage_info(anonymous_user_id)
    return UsageResponse(**info)


@router.post("/share-reward", response_model=ShareRewardResponse)
async def claim_share_reward(request: ShareRewardRequest):
    """Claim a share reward (bonus analysis count). Non-blocking — errors don't block UX."""
    try:
        result = grant_share_reward(
            anonymous_user_id=request.anonymous_user_id,
            share_type=request.share_type,
            share_hash=request.share_hash,
        )
        return ShareRewardResponse(
            granted=result["granted"],
            bonus_count=result["bonus_count"],
            message=result["message"],
        )
    except Exception as e:
        logger.warning(f"Share reward claim failed: {e}")
        return ShareRewardResponse(granted=False, bonus_count=0, message="Reward claim failed")
