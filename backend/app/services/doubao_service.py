import json
import base64
import asyncio
import logging
import time
from typing import Optional
import httpx
from openai import AsyncOpenAI, APIStatusError
from app.schemas.chat import ChatAnalysisResponse, ReplySuggestions, ChatStatus

logger = logging.getLogger(__name__)

# Error codes that indicate model quota/exhaustion → try next model
_QUOTA_ERROR_CODES = {429, 403, 503}
_QUOTA_ERROR_SUBSTRINGS = ["quota", "rate_limit", "ModelNotOpen", "insufficient", "capacity"]

# Alert cooldown tracker: {alert_key: last_sent_timestamp}
_alert_cooldown: dict[str, float] = {}


SYSTEM_PROMPT_ZH = """你是社交沟通分析助手。分析聊天氛围并给回复建议。
对方用"他/她:"，用户用"我:"。
分析：1.互动度 2.对方主动性 3.情绪反馈 4.问题 5.风险
禁止：判断喜欢、编造、情感操控、PUA
回复≤2句，自然可发送。
只输出JSON。"""

SYSTEM_PROMPT_EN = """You are a social communication analyst. Analyze chat vibes and suggest replies.
Other party: "he/she:", user: "me:".
Analyze: 1.engagement 2.initiative 3.emotion 4.issues 5.risks
Prohibited: judging feelings, fabrication, manipulation, PUA
Reply: ≤2 sentences, natural, sendable.
Output JSON only."""

# ── Relationship-specific prompt additions ──

RELATIONSHIP_PROMPTS = {
    "romantic": "场景：恋爱/暧昧。关注：主动性、情绪氛围、节奏。禁止：绝对判断、情感操控。",
    "friend": "场景：朋友。关注：情绪、社交边界、冷场。禁止：恋爱化解读。",
    "family": "场景：家人。关注：沟通方式、冲突风险。禁止：心理诊断、立场偏袒。",
    "coworker": "场景：同事/工作。关注：专业度、职场边界。禁止：情绪化建议、非职业行为。",
    "other": "场景：通用关系。中立客观分析。",
}


SCREENSHOT_EXTRACT_PROMPT = """你是一个聊天截图文字提取助手。从聊天截图中提取所有可见的聊天消息。

要求：
1. 按时间顺序提取每条消息
2. 区分发言人：对方用"他/她:"，用户自己用"我:"标注
3. 保留表情符号文字描述（如 [笑哭]）
4. 忽略系统提示（如"对方正在输入"、时间戳等）
5. 仅输出聊天文字内容

输出格式：
他/她: 消息内容1
我: 消息内容2
他/她: 消息内容3
..."""


class DoubaoService:
    def __init__(self):
        from app.core.config import settings
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
        self.text_models = settings.TEXT_MODELS
        self.vision_models = settings.VISION_MODELS
        logger.info(f"Text models: {self.text_models}")
        logger.info(f"Vision models: {self.vision_models}")

    def _is_quota_error(self, error: Exception) -> bool:
        """Check if the error indicates model quota exhaustion."""
        if isinstance(error, APIStatusError):
            if error.status_code in _QUOTA_ERROR_CODES:
                return True
            if any(s in str(error).lower() for s in _QUOTA_ERROR_SUBSTRINGS):
                return True
        msg = str(error).lower()
        return any(s in msg for s in _QUOTA_ERROR_SUBSTRINGS)

    async def _send_alert(self, model_type: str, models: list[str], last_error: str):
        """Send alert via webhook when all models of a type are exhausted."""
        from app.core.config import settings
        if not settings.ALERT_WEBHOOK_URL:
            return

        # Cooldown check
        alert_key = f"model_exhausted_{model_type}"
        now = time.time()
        last_sent = _alert_cooldown.get(alert_key, 0)
        if now - last_sent < settings.ALERT_COOLDOWN_SECONDS:
            logger.info(f"Alert for {model_type} skipped (cooldown)")
            return

        _alert_cooldown[alert_key] = now

        title = f"⚠️ ChatVibe {model_type}模型全部不可用"
        detail = (
            f"模型类型: {model_type}\n"
            f"尝试模型: {', '.join(models)}\n"
            f"最后错误: {last_error[:200]}\n"
            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        payload = self._build_webhook_payload(title, detail)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(settings.ALERT_WEBHOOK_URL, json=payload)
                if resp.status_code < 300:
                    logger.info(f"Alert sent for {model_type}")
                else:
                    logger.warning(f"Alert webhook returned {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            logger.warning(f"Failed to send alert: {e}")

    def _build_webhook_payload(self, title: str, detail: str) -> dict:
        """Build webhook payload. Supports PushPlus, DingTalk, Feishu, WeChat Work bots."""
        from app.core.config import settings
        url = settings.ALERT_WEBHOOK_URL.lower()

        # PushPlus (WeChat personal push)
        if "pushplus.plus" in url:
            return {"token": settings.PUSHPLUS_TOKEN, "title": title, "content": detail, "template": "txt"}
        # DingTalk robot
        if "oapi.dingtalk.com" in url:
            return {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"### {title}\n{detail}"},
            }
        # Feishu robot
        if "open.feishu.cn" in url:
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": title}},
                    "elements": [{"tag": "markdown", "content": detail}],
                },
            }
        # WeChat Work robot
        if "qyapi.weixin.qq.com" in url:
            return {
                "msgtype": "markdown",
                "markdown": {"content": f"{title}\n{detail}"},
            }
        # Default: plain JSON
        return {"title": title, "detail": detail}

    async def analyze_chat(self, chat_content: str, relationship_type: str = "romantic", language: str = "zh") -> ChatAnalysisResponse:
        from app.core.config import settings
        system_prompt = SYSTEM_PROMPT_EN if language == "en" else SYSTEM_PROMPT_ZH
        user_prompt = self._build_user_prompt(chat_content, relationship_type, language)

        last_error = None
        for model in self.text_models:
            try:
                t_api_start = time.time()
                logger.info(f"Trying text model: {model} (lang={language})")
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                )

                t_api_end = time.time()
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Model returned empty response")

                logger.info(f"Text model {model} succeeded in {(t_api_end - t_api_start):.1f}s, output tokens={len(content)}")
                return self._parse_response(content, language)

            except Exception as e:
                last_error = e
                if self._is_quota_error(e) and model != self.text_models[-1]:
                    logger.warning(f"Text model {model} quota error, trying next: {str(e)}")
                    continue
                logger.error(f"Text model {model} error: {str(e)}")
                raise

        # All text models exhausted
        await self._send_alert("文本", self.text_models, str(last_error))
        raise last_error

    async def extract_text_from_screenshot(self, image_bytes: bytes, content_type: str = "image/png") -> str:
        """使用多模态模型从聊天截图中提取文字，支持多模型自动切换"""
        from app.core.config import settings
        t_encode_start = time.time()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        t_encode = time.time() - t_encode_start
        logger.info(f"Vision encode base64: {len(image_bytes)}B → {len(image_base64)} chars in {t_encode:.2f}s")

        # 根据 content_type 确定 MIME 类型，默认 image/png
        mime_type = content_type if content_type in (
            "image/png", "image/jpeg", "image/jpg", "image/webp",
        ) else "image/png"

        last_error = None
        for model in self.vision_models:
            logger.info(f"Trying vision model: {model}")
            # Retry up to 2 times per model for transient errors
            for attempt in range(3):
                try:
                    t_api_start = time.time()
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                                    },
                                    {
                                        "type": "text",
                                        "text": SCREENSHOT_EXTRACT_PROMPT,
                                    },
                                ],
                            }
                        ],
                        temperature=settings.VISION_TEMPERATURE,
                        max_tokens=settings.VISION_MAX_TOKENS,
                    )

                    t_api = time.time() - t_api_start
                    content = response.choices[0].message.content
                    if not content:
                        raise ValueError("Vision model returned empty response")

                    logger.info(f"Vision model {model} succeeded on attempt {attempt + 1} in {t_api:.1f}s, output={len(content)} chars")
                    return content.strip()

                except Exception as e:
                    last_error = e
                    # Quota error → skip to next model immediately
                    if self._is_quota_error(e):
                        logger.warning(f"Vision model {model} quota error, trying next: {str(e)}")
                        break
                    # Transient error → retry same model
                    logger.warning(f"Vision model {model} attempt {attempt + 1} failed: {str(e)}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)

        logger.error(f"All vision models failed: {str(last_error)}")
        await self._send_alert("视觉", self.vision_models, str(last_error))
        raise last_error

    def _build_user_prompt(self, chat_content: str, relationship_type: str = "romantic", language: str = "zh") -> str:
        relationship_extra = RELATIONSHIP_PROMPTS.get(relationship_type, RELATIONSHIP_PROMPTS["other"])
        if language == "en":
            return f"""{relationship_extra}

Chat:
---
{chat_content}
---

Output JSON (no markdown):
{{"chat_status":"engaged|normal|polite|cold|high risk","analysis":"3-5 reasons","issues":[],"risks":[],"reply_suggestions":{{"natural":"reply","humorous":"reply","mature":"reply"}},"timing_advice":"advice"}}

Rules: pick one chat_status, empty issues/risks=[], replies ≤2 sentences natural. No judging feelings/PUA."""
        return f"""{relationship_extra}

聊天：
---
{chat_content}
---

输出JSON(不要markdown包裹):
{{"chat_status":"积极互动|普通互动|礼貌回应|偏冷淡|对话风险较高","analysis":"分析","issues":[],"risks":[],"reply_suggestions":{{"natural":"回复","humorous":"回复","mature":"回复"}},"timing_advice":"建议"}}

要求：必须选一个chat_status，issues/risks空则[]，回复≤2句话自然可发送。禁止判断喜欢/PUA。"""

    def _parse_response(self, raw_json: str, language: str = "zh") -> ChatAnalysisResponse:
        # Clean markdown code block wrappers
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Doubao JSON response: {raw_json[:200]}")
            raise ValueError(f"Invalid JSON from Doubao: {str(e)}")

        status_map_zh = {
            "积极互动": ChatStatus.POSITIVE,
            "普通互动": ChatStatus.NORMAL,
            "礼貌回应": ChatStatus.POLITE,
            "偏冷淡": ChatStatus.COLD,
            "对话风险较高": ChatStatus.HIGH_RISK,
        }
        status_map_en = {
            "engaged": ChatStatus.POSITIVE,
            "normal": ChatStatus.NORMAL,
            "polite": ChatStatus.POLITE,
            "cold": ChatStatus.COLD,
            "high risk": ChatStatus.HIGH_RISK,
        }
        status_map = {**status_map_zh, **status_map_en}

        raw_status = data.get("chat_status", "普通互动" if language == "zh" else "normal")
        chat_status = status_map.get(raw_status.strip().lower() if language == "en" else raw_status.strip())
        if chat_status is None:
            logger.warning(f"Unknown chat_status '{raw_status}', defaulting to NORMAL")
            chat_status = ChatStatus.NORMAL

        suggestions = data.get("reply_suggestions", {})
        default_fallbacks = {
            "natural": "Keep the conversation going naturally.",
            "humorous": "Respond in a light-hearted way.",
            "mature": "Maintain a composed and respectful tone.",
        } if language == "en" else {
            "natural": "可以自然地继续聊天。",
            "humorous": "用轻松的方式回应。",
            "mature": "保持稳重得体的交流。",
        }
        reply_suggestions = ReplySuggestions(
            natural=suggestions.get("natural", default_fallbacks["natural"]),
            humorous=suggestions.get("humorous", default_fallbacks["humorous"]),
            mature=suggestions.get("mature", default_fallbacks["mature"]),
        )

        return ChatAnalysisResponse(
            chat_status=chat_status,
            analysis=data.get("analysis", "无法完成分析，请重试。"),
            issues=data.get("issues", []),
            risks=data.get("risks", []),
            reply_suggestions=reply_suggestions,
            timing_advice=data.get("timing_advice", "保持当前节奏。"),
        )
