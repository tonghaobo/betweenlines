import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.chat import (
    ChatAnalysisRequest,
    ChatAnalysisResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.openai_service import OpenAIService
from app.services.chat_cleaner import clean_chat_content, validate_chat_format, is_potentially_harmful
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


def get_openai_service() -> OpenAIService:
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_doubao_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="Doubao API key not configured. Please set OPENAI_API_KEY in .env",
        )
    return OpenAIService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
    )


@router.post("/analyze", response_model=ChatAnalysisResponse)
async def analyze_chat(
    request: ChatAnalysisRequest,
    service: OpenAIService = Depends(get_openai_service),
):
    start_time = time.time()
    chat_length = len(request.chat_content)
    chat_status_result = None
    error_msg = None

    try:
        if len(request.chat_content.strip()) < settings.MIN_CHAT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Chat content must be at least {settings.MIN_CHAT_LENGTH} characters",
            )

        if len(request.chat_content) > settings.MAX_CHAT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Chat content must be at most {settings.MAX_CHAT_LENGTH} characters",
            )

        if is_potentially_harmful(request.chat_content):
            raise HTTPException(
                status_code=400,
                detail="内容包含不适当的请求。本工具仅用于正常社交沟通分析。",
            )

        cleaned_content = clean_chat_content(request.chat_content)
        warnings = validate_chat_format(cleaned_content)
        if warnings:
            logger.info(f"Chat format warnings: {warnings}")

        result = await service.analyze_chat(cleaned_content)
        chat_status_result = result.chat_status.value

        return result

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Analysis error: {error_msg}", exc_info=True)
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
            )
        except Exception as log_error:
            logger.warning(f"Failed to save analysis log: {log_error}")


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    try:
        from app.services.storage import save_feedback
        save_feedback(request.helpful, request.analysis_id)
    except Exception as e:
        logger.warning(f"Failed to save feedback: {e}")

    return FeedbackResponse(message="感谢你的反馈！")


@router.get("/stats")
async def get_stats():
    try:
        from app.services.storage import get_feedback_stats
        return get_feedback_stats()
    except Exception as e:
        logger.warning(f"Failed to get stats: {e}")
        return {"error": "Stats unavailable"}
