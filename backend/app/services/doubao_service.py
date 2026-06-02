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


SYSTEM_PROMPT = """你是一个专业的社交沟通分析助手。

你的目标：
帮助用户理解聊天状态，并给出自然沟通建议。

输入格式说明：
用户粘贴的聊天记录中，"他/她:" 或 "she/he:" 表示对方，"我:" 或 "me:" 表示用户自己。
请基于此理解对话双方的角色关系。

分析重点：
1. 互动积极程度
2. 对方主动性
3. 情绪反馈
4. 潜在聊天问题
5. 风险提醒
6. 回复建议

禁止：
• 判断喜欢程度
• 编造事实
• 情绪操控
• PUA 风格
• 极端两性观点

回复必须：
自然、现实、可执行。

回复建议规则：
- 每条回复不超过 2 句话
- 自然、可直接复制发送
- 不油腻、不尴尬
- 禁止套路话术

输出格式：
严格 JSON，不要输出任何非 JSON 内容。"""

# ── Relationship-specific prompt additions ──

RELATIONSHIP_PROMPTS = {
    "romantic": """
当前分析场景：恋爱/暧昧关系。

额外关注：
- 对方主动性和回复热情
- 情绪氛围和暧昧程度
- 聊天节奏是否合适
- 回复是否自然、不刻意

额外禁止：
- 绝对判断（如"她/他喜欢你"）
- 情感操控建议
- 过度解读对方意图
""",
    "friend": """
当前分析场景：朋友关系。

额外关注：
- 情绪状态是否正常
- 社交边界是否合适
- 是否存在误解或冷场
- 友谊维护建议

额外禁止：
- 恋爱化解读
- 过度分析暧昧信号
""",
    "family": """
当前分析场景：家人关系。

额外关注：
- 情绪缓和与沟通方式
- 表达是否清晰、不含攻击性
- 冲突风险与降温建议
- 家庭关系维护

额外禁止：
- 心理诊断
- 立场偏袒
- 煽动对抗
""",
    "coworker": """
当前分析场景：同事/工作关系。

额外关注：
- 沟通专业度
- 职场边界感
- 信息是否清晰、得体
- 潜在沟通风险（如误解、越界）

额外禁止：
- 情绪化建议
- 鼓励非职业行为
- 过度解读私人意图
""",
    "other": """
当前分析场景：通用关系。

请以中立、客观的方式分析沟通状态和提供建议。
""",
}


SCREENSHOT_EXTRACT_PROMPT = """你是一个聊天截图文字提取助手。

你的任务：
从聊天截图（可能是微信、QQ 等即时通讯工具的截图）中提取所有可见的聊天消息。

要求：
1. 按时间顺序逐条提取每条消息
2. 区分不同发言人：对方用"他/她:"，用户自己用"我:"。如果你无法判断谁是用户，对方用"他/她:"，自己用"我:"标注
3. 保留表情符号的文字描述（如 [笑哭]、[点赞]）
4. 忽略系统提示消息（如"对方正在输入"、时间戳、撤回提示等）
5. 仅输出聊天文字内容，不要输出任何其他说明

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

    async def analyze_chat(self, chat_content: str, relationship_type: str = "romantic") -> ChatAnalysisResponse:
        from app.core.config import settings
        user_prompt = self._build_user_prompt(chat_content, relationship_type)

        last_error = None
        for model in self.text_models:
            try:
                logger.info(f"Trying text model: {model}")
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Model returned empty response")

                logger.info(f"Text model {model} succeeded")
                return self._parse_response(content)

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
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

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

                    content = response.choices[0].message.content
                    if not content:
                        raise ValueError("Vision model returned empty response")

                    logger.info(f"Vision model {model} succeeded on attempt {attempt + 1}")
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

    def _build_user_prompt(self, chat_content: str, relationship_type: str = "romantic") -> str:
        relationship_extra = RELATIONSHIP_PROMPTS.get(relationship_type, RELATIONSHIP_PROMPTS["other"])
        return f"""请分析以下聊天记录。

{relationship_extra.strip()}

聊天内容：
---
{chat_content}
---

请以 JSON 格式输出分析结果。JSON schema 如下：
{{
  "chat_status": "积极互动 | 普通互动 | 礼貌回应 | 偏冷淡 | 对话风险较高",
  "analysis": "互动分析描述，说明为什么这样判断（3~5 个理由）",
  "issues": ["发现的聊天问题，如：提问密度过高、话题推进太快、自我输出不足等"],
  "risks": ["风险提醒，如：当前不建议连续追问"],
  "reply_suggestions": {{
    "natural": "自然版回复（最安全，不超过2句话）",
    "humorous": "幽默版回复（轻松风格，不超过2句话）",
    "mature": "成熟版回复（稳重有边界感，不超过2句话）"
  }},
  "timing_advice": "节奏建议，如：当前互动节奏正常，建议轻松延续话题，不建议突然升级关系"
}}

注意事项：
- chat_status 必须是枚举值之一
- issues 和 risks 如果为空请返回空数组 []
- 回复建议必须自然、可发送、不油腻
- 禁止判断喜欢程度
- 禁止使用 PUA 风格语言"""

    def _parse_response(self, raw_json: str) -> ChatAnalysisResponse:
        # 清理豆包可能输出的 markdown 代码块标记和前后多余文本
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            # 去除 ```json 或 ``` 开头
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

        status_map = {
            "积极互动": ChatStatus.POSITIVE,
            "普通互动": ChatStatus.NORMAL,
            "礼貌回应": ChatStatus.POLITE,
            "偏冷淡": ChatStatus.COLD,
            "对话风险较高": ChatStatus.HIGH_RISK,
        }

        raw_status = data.get("chat_status", "普通互动")
        chat_status = status_map.get(raw_status)
        if chat_status is None:
            logger.warning(f"Unknown chat_status '{raw_status}', defaulting to NORMAL")
            chat_status = ChatStatus.NORMAL

        suggestions = data.get("reply_suggestions", {})
        reply_suggestions = ReplySuggestions(
            natural=suggestions.get("natural", "可以自然地继续聊天。"),
            humorous=suggestions.get("humorous", "用轻松的方式回应。"),
            mature=suggestions.get("mature", "保持稳重得体的交流。"),
        )

        return ChatAnalysisResponse(
            chat_status=chat_status,
            analysis=data.get("analysis", "无法完成分析，请重试。"),
            issues=data.get("issues", []),
            risks=data.get("risks", []),
            reply_suggestions=reply_suggestions,
            timing_advice=data.get("timing_advice", "保持当前节奏。"),
        )
