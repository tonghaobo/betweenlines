"""Post-Reply Review service — compare previous analysis with new chat messages."""

import json
import time
import logging
from openai import AsyncOpenAI
import httpx

from app.core.config import settings
from app.schemas.chat import ReviewResponse, ConversationChanges

logger = logging.getLogger(__name__)

_shared_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _shared_http_client
    if _shared_http_client is None or _shared_http_client.is_closed:
        _shared_http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
            timeout=httpx.Timeout(60.0, connect=8.0),
        )
    return _shared_http_client


REVIEW_PROMPT_ZH = """你是一个客观的聊天观察员——你的任务是：对比用户上次的聊天记录和这次的后续聊天，判断上次的建议是否有效、关系有无改善。

你**不是在预测**感情、判断对方是否喜欢用户、或做任何情感结论。
你**只是在分析**可观察的对话模式变化。

比较维度（只看以下 5 个，不延伸）：
1. 主动性：对方是否更愿意主动开启/延续话题？（对比上次和本次）
2. 回复长度：对方回复是变长了还是变短了？
3. 情绪表达：对方使用表情、语气词、感叹号的频率是否有变化？
4. 冷场风险：对话是否仍然存在收口/终结趋势？
5. 话题衔接：对方是否更愿意接话、展开话题？

输出规则：
- review_status: improved（有明显改善） / similar（变化不大） / worsened（有降温趋势） / insufficient_data（数据不足）
- changes: 上述 5 个维度的变化方向（up/down/same），只列出有变化的部分
- previous_advice_effectiveness: 上次建议是否有效（"effective"/"partially_effective"/"ineffective"/"cannot_tell"）
- summary: 2-3句话中文总结，口语化，直接说观察到的事实
- next_step_advice: 1-2句下一步操作建议，可执行

严格禁止：
- ❌ 情感判断（"她更喜欢你了"/"有戏"/"没戏"）
- ❌ 制造焦虑（"关系要彻底凉了"）
- ❌ 伪精确概率（"改善概率73%"）
- ❌ 编造不在聊天中的事实

只输出纯JSON，不要markdown包裹。"""

REVIEW_PROMPT_EN = """You are an objective conversation observer. Your job: compare the user's previous chat with the new follow-up chat to assess whether the previous advice was effective and whether the relationship dynamic has shifted.

You are NOT predicting feelings, attraction, or relationship outcomes.
You ARE only analyzing observable conversation pattern changes.

Comparison dimensions (only these 5, no extensions):
1. Initiative: Is the other party more willing to initiate/continue topics? (compare before vs now)
2. Reply length: Did replies get longer or shorter?
3. Emotional engagement: Did emoji/emotional marker usage change?
4. Coldness risk: Is the conversation still showing door-closing signals?
5. Topic continuity: Is the other party more willing to pick up and expand on topics?

Output rules:
- review_status: improved / similar / worsened / insufficient_data
- changes: direction (up/down/same) for the 5 dimensions above, only list changed ones
- previous_advice_effectiveness: "effective" / "partially_effective" / "ineffective" / "cannot_tell"
- summary: 2-3 sentences in plain language, describing observed facts
- next_step_advice: 1-2 concrete actionable suggestions

Strictly prohibited:
- ❌ Emotional judgments ("they like you more now"/"you have a shot")
- ❌ Creating anxiety ("the relationship is doomed")
- ❌ Pseudo-precise probabilities ("73% improvement chance")
- ❌ Fabricating facts not in the chats

Output pure JSON only, no markdown wrapping."""


class ReviewService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            http_client=_get_http_client(),
        )
        self.text_models = settings.TEXT_MODELS

    def _parse_review_response(self, raw_json: str, language: str) -> ReviewResponse:
        """Parse LLM JSON response into ReviewResponse."""
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
            logger.error(f"Failed to parse review JSON: {raw_json[:200]}")
            raise ValueError(f"Invalid JSON from LLM: {str(e)}")

        valid_statuses = {"improved", "similar", "worsened", "insufficient_data"}
        raw_status = data.get("review_status", "similar")
        review_status = raw_status if raw_status in valid_statuses else "similar"

        changes_raw = data.get("changes", {})
        if not isinstance(changes_raw, dict):
            changes_raw = {}
        valid_dirs = {"up", "down", "same"}
        changes = ConversationChanges(
            initiative=changes_raw.get("initiative", "same") if changes_raw.get("initiative") in valid_dirs else "same",
            reply_length=changes_raw.get("reply_length", "same") if changes_raw.get("reply_length") in valid_dirs else "same",
            emotional_engagement=changes_raw.get("emotional_engagement", "same") if changes_raw.get("emotional_engagement") in valid_dirs else "same",
            coldness_risk=changes_raw.get("coldness_risk", "same") if changes_raw.get("coldness_risk") in valid_dirs else "same",
            topic_continuity=changes_raw.get("topic_continuity", "same") if changes_raw.get("topic_continuity") in valid_dirs else "same",
        )

        return ReviewResponse(
            review_status=review_status,
            changes=changes,
            previous_advice_effectiveness=str(data.get("previous_advice_effectiveness", "")),
            summary=str(data.get("summary", "")),
            next_step_advice=str(data.get("next_step_advice", "")),
        )

    async def compare_chat(
        self,
        previous_features: dict,
        new_chat_content: str,
        relationship_type: str = "romantic",
        language: str = "zh",
    ) -> ReviewResponse:
        """Compare previous analysis features with new chat content via LLM."""
        zh = language == "zh"
        system_prompt = REVIEW_PROMPT_EN if not zh else REVIEW_PROMPT_ZH

        # Build feature summary from previous analysis
        prev_summary = (
            f"上次分析特征：{previous_features.get('total_messages', '?')}条消息, "
            f"对方均长{previous_features.get('avg_other_len', '?')}字, "
            f"用户均长{previous_features.get('avg_user_len', '?')}字, "
            f"对方问句比{previous_features.get('other_question_ratio', '?')}%, "
            f"短回复比{previous_features.get('other_short_ratio', '?')}%, "
            f"情绪词: 积极{previous_features.get('sentiment_pos', 0)}/消极{previous_features.get('sentiment_neg', 0)}, "
            f"模式: {previous_features.get('notable_patterns', '未记录')}"
        ) if zh else (
            f"Previous analysis features: {previous_features.get('total_messages', '?')} msgs, "
            f"other avg {previous_features.get('avg_other_len', '?')} chars, "
            f"user avg {previous_features.get('avg_user_len', '?')} chars, "
            f"other Q% {previous_features.get('other_question_ratio', '?')}%, "
            f"short-reply {previous_features.get('other_short_ratio', '?')}%, "
            f"sentiment pos/neg {previous_features.get('sentiment_pos', 0)}/{previous_features.get('sentiment_neg', 0)}, "
            f"pattern: {previous_features.get('notable_patterns', 'not recorded')}"
        )

        user_prompt = (
            f"{'关系类型：' + relationship_type if zh else 'Relationship: ' + relationship_type}\n\n"
            f"{prev_summary}\n\n"
            f"{'=== 本次新的后续聊天 ===' if zh else '=== New follow-up chat ==='}:\n"
            f"{new_chat_content}\n\n"
            f"{'请对比上次和本次的聊天，判断关系是否改善。输出纯JSON。' if zh else 'Compare previous and new chat. Output JSON only.'}"
        )

        last_error = None
        for model in self.text_models:
            try:
                t_start = time.time()
                logger.info(f"Review: trying model {model}")
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=600,
                    timeout=45.0,
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Model returned empty response")

                result = self._parse_review_response(content, language)
                t_elapsed = time.time() - t_start
                logger.info(f"Review done ({model}): {t_elapsed:.1f}s, status={result.review_status}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Review model {model} error: {str(e)[:120]}")
                continue

        raise last_error
