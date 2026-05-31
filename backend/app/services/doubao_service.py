import json
import base64
import logging
from typing import Optional
from openai import AsyncOpenAI
from app.schemas.chat import ChatAnalysisResponse, ReplySuggestions, ChatStatus

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个专业的社交沟通分析助手。

你的目标：
帮助用户理解聊天状态，并给出自然沟通建议。

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


SCREENSHOT_EXTRACT_PROMPT = """你是一个聊天截图文字提取助手。

你的任务：
从聊天截图（可能是微信、QQ 等即时通讯工具的截图）中提取所有可见的聊天消息。

要求：
1. 按时间顺序逐条提取每条消息
2. 区分不同发言人（用 A: B: 格式，A 为对方，B 为用户自己；如果你无法判断谁是用户，用 A: B: 标注两个对话者）
3. 保留表情符号的文字描述（如 [笑哭]、[点赞]）
4. 忽略系统提示消息（如"对方正在输入"、时间戳、撤回提示等）
5. 仅输出聊天文字内容，不要输出任何其他说明

输出格式：
A: 消息内容1
B: 消息内容2
A: 消息内容3
..."""


class DoubaoService:
    def __init__(self):
        from app.core.config import settings
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
        self.model = settings.OPENAI_MODEL
        self.vision_model = settings.VISION_MODEL

    async def analyze_chat(self, chat_content: str) -> ChatAnalysisResponse:
        from app.core.config import settings
        user_prompt = self._build_user_prompt(chat_content)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Doubao returned empty response")

            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Doubao API error: {str(e)}")
            raise

    async def extract_text_from_screenshot(self, image_bytes: bytes) -> str:
        """使用多模态模型从聊天截图中提取文字"""
        from app.core.config import settings
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        try:
            response = await self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
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

            return content.strip()

        except Exception as e:
            logger.error(f"Vision API error: {str(e)}")
            raise

    def _build_user_prompt(self, chat_content: str) -> str:
        return f"""请分析以下聊天记录。

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
