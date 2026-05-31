import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from app.schemas.chat import (
    ChatAnalysisRequest,
    ChatAnalysisResponse,
    ScreenshotAnalysisResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.doubao_service import DoubaoService
from app.services.chat_cleaner import clean_chat_content, validate_chat_format, is_potentially_harmful
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
    request: ChatAnalysisRequest,
    service: DoubaoService = Depends(get_doubao_service),
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


@router.post("/analyze-screenshot", response_model=ScreenshotAnalysisResponse)
async def analyze_screenshot(
    file: UploadFile = File(...),
    service: DoubaoService = Depends(get_doubao_service),
):
    """上传聊天截图，提取文字并返回供用户确认"""
    start_time = time.time()

    # 验证文件类型
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式：{file.content_type}。请上传 PNG、JPEG 或 WebP 格式的图片。",
        )

    # 读取并验证文件大小
    image_bytes = await file.read()
    if len(image_bytes) > settings.MAX_SCREENSHOT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片过大（{len(image_bytes) / 1024 / 1024:.1f}MB），请上传不超过 10MB 的图片。",
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="上传的图片为空，请重新选择。")

    logger.info(f"Screenshot upload: {file.filename}, size={len(image_bytes)}, type={file.content_type}")

    try:
        extracted_text = await service.extract_text_from_screenshot(image_bytes)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"Screenshot text extracted in {duration_ms:.0f}ms, length={len(extracted_text)}")

        if not extracted_text or len(extracted_text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="未能从图片中提取到足够的聊天文字。请确保截图包含清晰的聊天消息。",
            )

        return ScreenshotAnalysisResponse(
            extracted_text=extracted_text.strip(),
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
