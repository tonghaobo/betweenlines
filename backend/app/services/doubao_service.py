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


SYSTEM_PROMPT_ZH = """你是社交沟通分析专家。你的任务是基于聊天记录，客观分析双方互动质量，并给出贴合原文的回复建议。

分析步骤（请按顺序思考）：
1. 整体感知：消息轮次、回复间隔、总体情绪基调
2. 双方对比：各发言几条？谁主导话题？是否互相回应？
3. 情绪识别：对方每句话背后的情绪（热情/平淡/回避/不耐烦）
4. 问题定位：是否存在冷场、敷衍、误解、话题枯竭？
5. 综合判断：给出 chat_status，确保与具体观察一致

输出质量要求：
- analysis：3-5 句具体观察，每句都应有原文支撑，禁止泛泛而谈（如"对方不太积极"应改为"对方连续回复都是单字'嗯'，无明显话题延伸"）
- issues：列出具体问题，每条≤20字，必须基于原文而非猜测
- risks：列出潜在风险（氛围恶化/误解加深/时机不当），空则为[]
- reply_suggestions：每种风格≤2句，必须呼应聊天中最新的1-2条消息，让人可以直接发送
- timing_advice：给出可操作的具体建议（如"等半小时再发"、"换一个话题方向"），而非"保持节奏"之类的废话

严格禁止：
- 判断对方是否喜欢你
- 任何 PUA / 情感操控话术
- 编造聊天记录中不存在的事实
- 使用模板化套话（如"祝你们越来越好"）
- 代替用户做决定
- 制造焦虑或恐吓

只输出纯 JSON，不要包裹在 markdown 代码块中。"""

SYSTEM_PROMPT_EN = """You are a social communication analysis expert. Your task is to objectively analyze chat interaction quality based on chat records and provide reply suggestions that fit the original text.

Analysis steps (think in order):
1. Overall perception: message turns, reply intervals, overall emotional tone
2. Comparison: who speaks more? Who dominates? Do they respond to each other?
3. Emotion recognition: the emotion behind each message from the other party (enthusiastic / flat / avoidant / impatient)
4. Problem identification: any coldness, perfunctory replies, misunderstandings, topic exhaustion?
5. Comprehensive judgment: assign chat_status, ensuring consistency with specific observations

Output quality requirements:
- analysis: 3-5 specific observations, each must be supported by the original text; avoid vague statements (e.g. instead of "the other party is not very active", say "the other party replied with single-word 'ok' 3 times in a row, showing no topic extension")
- issues: list specific problems, each ≤20 words, must be based on text not speculation
- risks: list potential risks (atmosphere worsening / misunderstanding deepening / bad timing), empty if none
- reply_suggestions: each style ≤2 sentences, must echo the latest 1-2 messages in the chat, ready to send
- timing_advice: give actionable specific advice (e.g. "wait 30 minutes before replying", "switch to a different topic"), not vague phrases like "keep the current pace"

Strictly prohibited:
- Judging whether someone has feelings for the user
- Any PUA / emotional manipulation tactics
- Fabricating facts not present in the chat
- Using templated clichés
- Making decisions on behalf of the user
- Creating anxiety or fear

Output pure JSON only, do NOT wrap in markdown code blocks."""

# ── Static few-shot examples (compact, quality reference only) ──

_FEWSHOT_ZH = """=== Few-Shot 质量参考 ===

示例1：
输入：他: 今天加班好累啊 / 我: 辛苦了，晚饭吃了吗 / 他: 还没，准备点外卖 / 我: 我也没吃，一起点？
输出：{"chat_status":"积极互动","analysis":"1.对方主动分享状态（'加班好累'），自我表露=互动意愿。2.用户顺势关心+提出共同行动（'一起点'），转换流畅。3.对方'准备点外卖'而非结束对话，说明愿意继续。","issues":[],"risks":[],"reply_suggestions":{"natural":"你想吃啥？我可以推荐几家附近的","humorous":"外卖小哥又要奔波了哈哈，快点点吧","mature":"先填饱肚子，其他事等会再聊"},"timing_advice":"对方愿意聊，建议立即回复"}

示例2：
输入：我: 周末有什么安排吗 / 他: 没有 / 我: 最近有部电影还不错 / 他: 哦 / 我: 你喜欢看电影吗 / 他: 还行
输出：{"chat_status":"偏冷淡","analysis":"1.对方连续3条单字/双字回复（'没有''哦''还行'），典型的敷衍模式。2.用户连续追问3次，对方均未延伸话题。3.零表情/零语气词，情绪反馈极弱。","issues":["用户连续追问给对方压力","话题未引起对方兴趣"],"risks":["继续追问可能让对方更冷淡","可能产生负面印象"],"reply_suggestions":{"natural":"好的，那你先忙，有空再聊","humorous":"看来今天不在状态哈哈，改天约","mature":"了解，不打扰你了，有空联系"},"timing_advice":"立即停止追问，等对方主动开启话题"}
==="""

_FEWSHOT_EN = """=== Few-Shot Quality Reference ===

Example 1:
Input: him: worked overtime today, so tired / me: that's rough, did you eat dinner / him: not yet, gonna order takeout / me: me neither, order together?
Output: {"chat_status":"engaged","analysis":"1.Other person self-discloses ('so tired'), signaling engagement. 2.User shifts from empathy to joint action ('order together'), a smooth transition. 3.'Gonna order takeout' (vs 'gotta go') shows openness to continue.","issues":[],"risks":[],"reply_suggestions":{"natural":"What are you in the mood for? I can recommend nearby","humorous":"The delivery guy's gonna be busy haha, order quick","mature":"Let's eat first, other things can wait"},"timing_advice":"Reply now while the conversation is warm"}

Example 2:
Input: me: any plans for the weekend / her: nope / me: there's a good movie / her: oh / me: do you like movies / her: kinda
Output: {"chat_status":"cold","analysis":"1.Three consecutive single-word replies ('nope''oh''kinda'), clear disengagement. 2.User asks three questions, none elicit topic extension. 3.Zero emotional cues, extremely low engagement.","issues":["Rapid-fire questions may feel pressuring","Topics fail to spark interest"],"risks":["Continued questioning may worsen dynamic","Perceived as pushy"],"reply_suggestions":{"natural":"Alright, you seem busy — catch up another time","humorous":"Not your day today huh, no worries","mature":"Understood, I'll let you go. Reach out when free"},"timing_advice":"Stop initiating, wait for the other party to start next time"}
==="""

# ── Relationship-specific prompt additions ──

RELATIONSHIP_PROMPTS = {
    "romantic": (
        "场景：恋爱/暧昧关系。\n"
        "分析重点：\n"
        "- 对方是否有分享欲（主动分享日常=兴趣信号）\n"
        "- 回复速度变化趋势（突然变快/变慢往往有含义）\n"
        "- 情绪词和表情使用频率\n"
        "节奏建议区分阶段：刚认识（不宜过频，每1-2天1次自然互动）→ "
        "暧昧期（可适度推进，关注对方回应质量）→ "
        "恋爱中（关注情绪需求，别忽视'潜台词'）\n"
        "禁止：绝对判断（'她喜欢你'/'她不喜欢你'）、情感操控、过度解读"
    ),
    "friend": (
        "场景：朋友关系。\n"
        "分析重点：\n"
        "- 互动频率是否对等（单方面主动太多=信号）\n"
        "- 是否有'敷衍三连'（嗯/哦/好的）\n"
        "- 共同话题深度（是否愿意聊私人话题）\n"
        "注意：朋友间的冷淡未必是关系问题，可能只是各自忙\n"
        "禁止：恋爱化解读（把朋友互动解读为暧昧）、过度分析"
    ),
    "family": (
        "场景：家人关系。\n"
        "分析重点：\n"
        "- 沟通方式是否健康（指责 vs 表达感受）\n"
        "- 是否有未表达的期待（'算了不说了'=情绪积压）\n"
        "- 代际沟通模式差异\n"
        "建议原则：缓和而非激化、理解而非站队\n"
        "禁止：心理诊断、立场偏袒、激化矛盾"
    ),
    "coworker": (
        "场景：同事/职场关系。\n"
        "分析重点：\n"
        "- 专业度保持（是否过度情绪化）\n"
        "- 职场边界（是否越界的私人话题）\n"
        "- 效率导向（沟通是否清晰直接）\n"
        "回复建议原则：简洁专业、保持边界、不制造误会\n"
        "禁止：情绪化建议、非职业行为建议、引发办公室政治"
    ),
    "other": (
        "场景：通用社交关系。\n"
        "中立客观分析，不做关系假设。\n"
        "关注：尊重、边界、互动质量\n"
        "禁止：预设关系类型、过度解读"
    ),
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


# Shared HTTP client with connection pooling for keep-alive across requests.
# Eliminates ~200-500ms TCP+TLS handshake on every API call.
_shared_http_client: httpx.AsyncClient | None = None

def _get_http_client() -> httpx.AsyncClient:
    """Get or create shared httpx client with connection pooling."""
    global _shared_http_client
    if _shared_http_client is None or _shared_http_client.is_closed:
        _shared_http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
            timeout=httpx.Timeout(30.0, connect=8.0),
        )
    return _shared_http_client


class DoubaoService:
    def __init__(self):
        from app.core.config import settings
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            http_client=_get_http_client(),
        )
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
        t0_total = time.time()

        # ── Build prompts (CPU only) ──
        t0 = time.time()
        system_prompt = SYSTEM_PROMPT_EN if language == "en" else SYSTEM_PROMPT_ZH
        user_prompt = self._build_user_prompt(chat_content, relationship_type, language)
        t_build = time.time() - t0
        logger.info(f"[Timing] Prompt build: {t_build:.3f}s, system={len(system_prompt)}c, user={len(user_prompt)}c")

        last_error = None
        for model in self.text_models:
            try:
                t_api_start = time.time()
                logger.info(f"[Timing] Trying model: {model} (lang={language})")
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                    timeout=20.0,  # Per-model timeout to prevent hanging
                )

                t_api = time.time() - t_api_start
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Model returned empty response")

                # ── Parse response ──
                t0 = time.time()
                result = self._parse_response(content, language)
                t_parse = time.time() - t0

                t_total = time.time() - t0_total
                logger.info(
                    f"[Timing] {model} done: api={t_api:.1f}s, parse={t_parse:.3f}s, "
                    f"total={t_total:.1f}s, input_tokens={response.usage.prompt_tokens if response.usage else '?'}, "
                    f"output_tokens={response.usage.completion_tokens if response.usage else '?'}"
                )
                return result

            except Exception as e:
                last_error = e
                t_elapsed = time.time() - t0_total
                if self._is_quota_error(e) and model != self.text_models[-1]:
                    logger.warning(f"[Timing] {model} quota error @ {t_elapsed:.1f}s, trying next: {str(e)[:80]}")
                    continue
                logger.error(f"[Timing] {model} error @ {t_elapsed:.1f}s: {str(e)[:120]}")
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
                        timeout=20.0,
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

    def _extract_chat_features(self, chat_content: str) -> dict:
        """Extract structured features from chat text for AI reference. Pure CPU, <1ms."""
        import re

        lines = [l.strip() for l in chat_content.split('\n') if l.strip()]
        user_msgs = [l for l in lines if l.startswith(('我:', '我：'))]
        other_msgs = [l for l in lines if l.startswith(('他:', '他：', '她:', '她：'))]

        avg_user_len = round(sum(len(m) for m in user_msgs) / max(len(user_msgs), 1), 1)
        avg_other_len = round(sum(len(m) for m in other_msgs) / max(len(other_msgs), 1), 1)

        # --- Emoji / emoticon detection ---
        emoji_pattern = re.compile(
            r'[\U0001F300-\U0001F9FF]'       # Emoticons, symbols, pictographs
            r'|[\u2600-\u27BF]'               # Misc symbols
            r'|[\uFE00-\uFE0F]'               # Variation selectors
            r'|[\U0001FA00-\U0001FAFF]'       # Extended-A
            r'|\[[\u4e00-\u9fff\w]+\]',        # Chinese bracket emoji [笑哭]
            re.UNICODE,
        )
        other_emoji_count = sum(len(emoji_pattern.findall(m)) for m in other_msgs)
        user_emoji_count = sum(len(emoji_pattern.findall(m)) for m in user_msgs)

        # --- Short-reply ratio (≤3 chars after stripping prefix) ---
        def _strip_prefix(msg: str) -> str:
            return re.sub(r'^(他|她|我)\s*[：:]\s*', '', msg)

        other_short = sum(1 for m in other_msgs if len(_strip_prefix(m)) <= 3)
        other_short_ratio = round(other_short / max(len(other_msgs), 1) * 100, 1)

        # --- Sentiment indicator word analysis ---
        positive_words = ['哈哈', '嘻嘻', '开心', '好呀', '嗯嗯', '好的呀',
                          '太好了', '棒', '喜欢', '期待', '嘿嘿', '没错']
        negative_words = ['嗯', '哦', '好吧', '随便', '算了', '行吧',
                          '知道了', '无所谓', '随便你', '哦哦']
        pos_count = sum(1 for m in other_msgs if any(w in m for w in positive_words))
        neg_count = sum(1 for m in other_msgs if any(w in m for w in negative_words))

        # --- Topic coherence: does other party reference prior topics? ---
        topic_ref_words = ['刚才', '刚刚', '那个', '这个', '你说的', '之前', '上次']
        topic_refs = sum(1 for m in other_msgs if any(w in m for w in topic_ref_words))
        topic_coherence = round(topic_refs / max(len(other_msgs), 1) * 100, 1)

        # --- Question ratio (added '呢' for rhetorical questions) ---
        other_questions = sum(1 for m in other_msgs if '?' in m or '？' in m or '吗' in m or '呢' in m)
        other_question_ratio = round(other_questions / max(len(other_msgs), 1) * 100, 1)

        # --- Notable patterns ---
        patterns = []
        if avg_other_len <= 5 and len(other_msgs) >= 2:
            patterns.append(f"对方回复极短(均长{avg_other_len}字)，可能缺乏兴趣或正在忙")
        if other_short_ratio >= 50 and len(other_msgs) >= 2:
            patterns.append(f"对方{other_short_ratio}%回复≤3字，敷衍信号较强")
        if avg_user_len >= avg_other_len * 3 and len(user_msgs) >= 2 and len(other_msgs) >= 2:
            patterns.append("用户发送显著长于对方，话题可能由用户单方面推动")
        if other_question_ratio >= 40:
            patterns.append(f"对方积极提问(问句占比{other_question_ratio}%)，互动意愿较高")
        if len(user_msgs) >= len(other_msgs) * 3 and len(other_msgs) >= 2:
            patterns.append("用户发送频率远高于对方，注意节奏控制")
        if other_emoji_count >= len(other_msgs) * 0.4 and len(other_msgs) >= 2:
            patterns.append(f"对方频繁使用表情({other_emoji_count}次)，情绪表达丰富")
        if pos_count >= len(other_msgs) * 0.5 and len(other_msgs) >= 2:
            patterns.append("对方积极情绪词较多(哈哈/好呀/嗯嗯等)，氛围偏正面")
        if neg_count >= len(other_msgs) * 0.3 and len(other_msgs) >= 2:
            patterns.append("对方使用了冷淡/敷衍用词(嗯/哦/好吧等)，需注意氛围")
        if topic_coherence >= 30:
            patterns.append("对方积极回应之前话题，交流有连贯性")
        if user_emoji_count >= len(user_msgs) * 0.3 and len(user_msgs) >= 2:
            patterns.append("用户主动使用表情调节氛围，沟通风格较轻松")

        return {
            'total_messages': len(lines),
            'total_rounds': max(len(user_msgs), len(other_msgs)),
            'user_msgs': len(user_msgs),
            'other_msgs': len(other_msgs),
            'avg_user_len': avg_user_len,
            'avg_other_len': avg_other_len,
            'other_question_ratio': other_question_ratio,
            'other_emoji_count': other_emoji_count,
            'user_emoji_count': user_emoji_count,
            'other_short_ratio': other_short_ratio,
            'sentiment_pos': pos_count,
            'sentiment_neg': neg_count,
            'topic_coherence': topic_coherence,
            'notable_patterns': '; '.join(patterns) if patterns else '无明显异常模式',
        }

    def _get_dynamic_fewshot(self, relationship_type: str, language: str, limit: int = 2) -> str:
        """Fetch recent user-approved good cases from DB and format as few-shot examples.

        Only includes extracted features (not raw chat content) per privacy policy.
        Now includes quality_reason (why user found it helpful) and enhanced features.
        Returns empty string if no cases available or storage fails (non-blocking).
        """
        try:
            from app.services.storage import get_good_cases
            cases = get_good_cases(relationship_type=relationship_type, language=language, limit=limit)
            if not cases:
                return ""

            zh = language == "zh"
            header = ("\n=== 用户认可的优秀分析案例（请参照此质量水平）===\n" if zh else
                      "\n=== User-Approved Quality Examples (match this quality) ===\n")
            parts = [header]

            for i, case in enumerate(cases):
                label = f"案例{i + 1}" if zh else f"Case {i + 1}"
                sentiment_info = ""
                if zh:
                    sentiment_info = (
                        f", 表情{case.get('other_emoji_count', 0)}次"
                        f", 简短回复比{case.get('other_short_ratio', 0)}%"
                        f", 情绪词: 积极{case.get('sentiment_pos', 0)}/消极{case.get('sentiment_neg', 0)}"
                        f", 话题连贯性{case.get('topic_coherence', 0)}%"
                    )
                else:
                    sentiment_info = (
                        f", emoji {case.get('other_emoji_count', 0)}"
                        f", short-reply {case.get('other_short_ratio', 0)}%"
                        f", sentiment pos/neg {case.get('sentiment_pos', 0)}/{case.get('sentiment_neg', 0)}"
                        f", coherence {case.get('topic_coherence', 0)}%"
                    )

                if zh:
                    parts.append(
                        f"{label}：{case['total_messages']}条消息, "
                        f"对方{case['other_msgs']}条(均长{case['avg_other_len']}字), "
                        f"用户{case['user_msgs']}条(均长{case['avg_user_len']}字), "
                        f"问句比{case['other_question_ratio']}%{sentiment_info}, "
                        f"模式: {case['notable_patterns']}"
                    )
                else:
                    parts.append(
                        f"{label}: {case['total_messages']} msgs, "
                        f"other {case['other_msgs']} msgs (avg {case['avg_other_len']} chars), "
                        f"user {case['user_msgs']} msgs (avg {case['avg_user_len']} chars), "
                        f"Q ratio {case['other_question_ratio']}%{sentiment_info}, "
                        f"pattern: {case['notable_patterns']}"
                    )

                # Include quality reason if available (why user found it helpful)
                quality_reason = case.get('quality_reason', '')
                if quality_reason:
                    reason_label = "用户认可理由" if zh else "User-approved reason"
                    parts.append(f"{reason_label}：{quality_reason}")

                parts.append(f"{'优秀输出' if zh else 'Excellent output'}：\n{case['analysis_json']}\n")

            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"Failed to fetch good cases for few-shot: {e}")
            return ""

    def _build_user_prompt(self, chat_content: str, relationship_type: str = "romantic", language: str = "zh") -> str:
        relationship_extra = RELATIONSHIP_PROMPTS.get(relationship_type, RELATIONSHIP_PROMPTS["other"])
        features = self._extract_chat_features(chat_content)
        fewshot_static = _FEWSHOT_EN if language == "en" else _FEWSHOT_ZH
        fewshot_dynamic = self._get_dynamic_fewshot(relationship_type, language, limit=1)

        # Feature summary line for the prompt (compact)
        sentiment_line = (
            f"Sentiment: pos={features['sentiment_pos']}/neg={features['sentiment_neg']}, "
            f"coherence={features['topic_coherence']}%"
            if language == "en" else
            f"情绪词: 积极{features['sentiment_pos']}个/消极{features['sentiment_neg']}个, "
            f"话题连贯性{features['topic_coherence']}%"
        )
        emoji_line = (
            f"Emoji: other={features['other_emoji_count']}, user={features['user_emoji_count']}"
            if language == "en" else
            f"表情使用: 对方{features['other_emoji_count']}次/用户{features['user_emoji_count']}次"
        )

        if language == "en":
            return f"""{relationship_extra}

{fewshot_static}
{fewshot_dynamic}
Chat ({features['total_messages']} messages, ~{features['total_rounds']} rounds):
---
{chat_content}
---

Key features: other {features['other_msgs']}msgs(avg{features['avg_other_len']}c,{features['other_short_ratio']}%short), user {features['user_msgs']}msgs(avg{features['avg_user_len']}c), Q%={features['other_question_ratio']}%, {emoji_line}, {sentiment_line}
Patterns: {features['notable_patterns']}

Output JSON only (no markdown). Follow system prompt quality rules."""
        return f"""{relationship_extra}

{fewshot_static}
{fewshot_dynamic}
聊天记录（{features['total_messages']}条/{features['total_rounds']}轮）：
---
{chat_content}
---

关键特征：对方{features['other_msgs']}条（均长{features['avg_other_len']}字,{features['other_short_ratio']}%短回复），用户{features['user_msgs']}条（均长{features['avg_user_len']}字），问句比{features['other_question_ratio']}%，{emoji_line}，{sentiment_line}
模式：{features['notable_patterns']}

输出纯JSON（不要markdown），遵守系统指令中的质量要求。"""

    def _check_analysis_quality(self, data: dict, language: str) -> list[str]:
        """Post-hoc quality validation. Logs warnings for low-quality outputs.

        Pure CPU, <1ms. Non-blocking — only logs warnings, never rejects output.
        Returns list of warning messages for observability.
        """
        warnings = []
        zh = language == "zh"

        analysis = data.get("analysis", "")
        if isinstance(analysis, list):
            analysis = " ".join(str(a) for a in analysis)
        analysis_str = str(analysis).lower()

        # Check 1: Generic/template cliché phrases in analysis
        generic_zh = ["祝你们越来越好", "保持当前", "祝你好运"]
        generic_en = ["keep it up", "good luck"]
        generic = generic_zh if zh else generic_en
        for phrase in generic:
            if phrase.lower() in analysis_str:
                warnings.append(f"Generic phrase in analysis: '{phrase}'")

        # Check 2: Does analysis reference specific chat lines?
        has_quote = any(c in str(analysis) for c in ['"', '"', '「', '」', "'"])
        has_specific_ref = (
            ('条' in str(analysis) and any(c.isdigit() for c in str(analysis)))
            or ('次' in str(analysis) and any(c.isdigit() for c in str(analysis)))
            or ('轮' in str(analysis) and any(c.isdigit() for c in str(analysis)))
            or ('句' in str(analysis))
        ) if zh else (
            ('time' in analysis_str or 'reply' in analysis_str)
            and any(c.isdigit() for c in str(analysis))
        )
        if not (has_quote or has_specific_ref):
            warnings.append("Analysis lacks specific text references or quotes")

        # Check 3: Reply suggestions — are they the generic fallback?
        suggestions = data.get("reply_suggestions", {})
        fallback_zh = {
            "natural": "可以自然地继续聊天。",
            "humorous": "用轻松的方式回应。",
            "mature": "保持稳重得体的交流。",
        }
        fallback_en = {
            "natural": "Keep the conversation going naturally.",
            "humorous": "Respond in a light-hearted way.",
            "mature": "Maintain a composed and respectful tone.",
        }
        fallbacks = fallback_zh if zh else fallback_en
        for style, content in suggestions.items():
            if isinstance(content, str) and content.strip() == fallbacks.get(style, "").strip():
                warnings.append(f"Reply '{style}' is generic fallback (no personalization)")

        # Check 4: Vague timing advice
        vague_zh = ["保持节奏", "顺其自然", "看情况"]
        vague_en = ["keep the pace", "go with the flow", "play it by ear"]
        vague = vague_zh if zh else vague_en
        timing = data.get("timing_advice", "")
        if isinstance(timing, str):
            for phrase in vague:
                if phrase.lower() in timing.lower():
                    warnings.append(f"Vague timing advice: '{phrase}'")

        if warnings:
            logger.warning(f"Analysis quality issues ({len(warnings)}): {'; '.join(warnings)}")

        return warnings

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

        # Coerce types: AI sometimes returns analysis as list or timing_advice as None
        raw_analysis = data.get("analysis", "无法完成分析，请重试。")
        if isinstance(raw_analysis, list):
            raw_analysis = " ".join(str(a) for a in raw_analysis)
        if not isinstance(raw_analysis, str):
            raw_analysis = str(raw_analysis)

        raw_issues = data.get("issues", [])
        if isinstance(raw_issues, str):
            raw_issues = [raw_issues]
        if not isinstance(raw_issues, list):
            raw_issues = []

        raw_risks = data.get("risks", [])
        if isinstance(raw_risks, str):
            raw_risks = [raw_risks]
        if not isinstance(raw_risks, list):
            raw_risks = []

        raw_timing = data.get("timing_advice", "保持当前节奏。")
        if not raw_timing or not isinstance(raw_timing, str):
            raw_timing = "保持当前节奏。" if language == "zh" else "Keep the current pace."

        # Post-hoc quality check (non-blocking, log-only)
        self._check_analysis_quality(data, language)

        return ChatAnalysisResponse(
            chat_status=chat_status,
            analysis=raw_analysis,
            issues=raw_issues,
            risks=raw_risks,
            reply_suggestions=reply_suggestions,
            timing_advice=raw_timing,
        )
