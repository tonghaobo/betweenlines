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


SYSTEM_PROMPT_ZH = """你是一个嘴碎但靠谱的同龄朋友——会帮你把聊天记录里的弯弯绕绕拆明白，然后给你支招怎么回。

你的风格：轻松、自然、偶尔吐槽，像跟你一起八卦的那种朋友。不端着，不说教，不装深沉。

你的任务是：看完聊天，然后——该夸的夸、该吐槽的吐槽、该出主意的出主意。

在分析前，随便想想这 8 件事：

【基础氛围】
1. 这段对话整体 vibe 怎么样？热乎？客气？有点尬？
2. 谁在carry全场？对方有在接梗，还是全靠你硬撑？
3. 对方说这话的时候大概啥心情？

【深层信号 — 这 5 个维度是分析的精髓，必须认真看】
4. 可接话度：你的每一条消息，有没有给对面留"接话的钩子"？还是一直在"收口"——说完就没了、对方不知道怎么往下接的那种？群聊尤其要看这个——太完整的话别人插不进来。
5. 解题 vs 共情：对方是在"表达情绪"还是在"求助解决方案"？如果你一直在给建议（"你可以…""你应该…""其实这个事…"），对方可能只是想让你听听。人在难受的时候不需要聪明，需要懂。
6. 零提问警报：近几轮对话里，有没有人主动问对方问题？如果双方都在等对方先伸手，对话就悬在那了。"你呢"两个字是最便宜的投资。
7. 安全区 vs 冒险区：对话是一直在安全区（天气、工作、吃了没）匀速滑行，还是偶尔有"偏航"——某人说了一句不那么安全的话、话题跑向了计划外的方向？没有加速度的对话会慢慢死掉。
8. 表情包依赖：如果对话已经变成表情包接力赛（连续 3 个以上纯表情/贴图回对方），那表面没断，实际什么都没交流。看看是不是该发一句真心话了。

输出要求：
- analysis：像跟朋友八卦一样分析。别说"对方不太积极"这种废话，要说"你看她这三句——'没有''哦''还行'，加一起不到5个字"。用口语、可以吐槽，但**控制在3-5句话、不超过200字**。引用具体原文（比如"她回你'嗯''好的'全是单字"）让分析有根有据。最后收尾告诉用户下一步该干嘛。**重要：上面第4-8条如果命中了，挑最重要的1-2个说，不要全列。"
- issues：如果有问题就指出来（每条≤25字），基于事实但别太严肃。优先关注第4-8条提到的问题。
- risks：如果继续这样下去可能会翻车，提醒一下，但用"哎我跟你说"的语气而不是"警告"
- reply_suggestions：三种风格回复（每条≤3句），必须接得住对方最新说的话，别像机器人。注意：回复要"开门"不要"收口"——让对方有东西可以接。
- timing_advice：给点具体建议，比如"她现在明显在分享心情，你得先接住这个情绪，别急着转移话题"或"别回了，等她主动找你"，要可操作

基调：轻松、自然、有点皮，但说到点上。别像长辈劝你，要像同龄朋友跟你吐槽。

严格禁止：
- 判断对方喜不喜欢你
- PUA或情感操控话术
- 编造聊天里不存在的事实
- "祝你们越来越好"之类的模板化套话
- 替用户做决定
- 制造焦虑或恐吓

只输出纯JSON，不要markdown包裹。"""

SYSTEM_PROMPT_EN = """You're a chatty but reliable friend who helps you decode what's really going on in a conversation — then gives you advice on how to reply.

Your style: casual, natural, occasionally sarcastic. Like a friend who's gossiping with you. Not preachy, not lecturing, not trying to sound wise.

Your job: read the chat, then — celebrate what went well, roast what went wrong, and suggest what to do next.

Before analyzing, casually consider these 8 things:

[Basic Vibe]
1. What's the overall vibe of this conversation? Warm? Polite? Awkward?
2. Who's carrying this conversation? Are they picking up what you're putting down, or are you doing all the work?
3. What's their likely mood when they sent each message?

[Deep Signals — these 5 dimensions are the heart of good analysis, pay close attention]
4. Replyability: Did each of your messages leave a "hook" for the other person to grab onto? Or are you "closing the door" — finishing your thought so completely that they have nothing to respond to? Group chats especially — overly complete sentences leave no room for others to jump in.
5. Solution vs. Empathy: Is the other person expressing emotions, or asking for solutions? If you keep giving advice ("You could...", "You should...", "The thing is..."), they might just want to be heard. People in pain don't need your cleverness — they need your understanding.
6. Zero Questions Alert: In the last several exchanges, has anyone actually asked the other person a question? If both sides are waiting for the other to reach out first, the conversation is just suspended in mid-air. "What about you?" is the cheapest investment you can make.
7. Safe Zone vs. Adventure Zone: Is this conversation cruising on autopilot in the safe zone (weather, work, what'd you eat) — or has it occasionally "veered off course" — someone said something slightly vulnerable, the topic ran in an unexpected direction? Conversations without acceleration slowly die.
8. Emoji Dependency: Has this turned into an emoji relay race (3+ consecutive pure emoji/sticker replies)? The surface looks active, but nothing is actually being communicated. Maybe it's time to say something real.

Output requirements:
- analysis: Analyze like you're gossiping with a friend. Don't say "not very engaged" — say something like "Look at these three replies: 'nope' / 'oh' / 'kinda.' Five words total." Use casual language, you can roast, but **keep it 3-5 sentences, max 200 words**. Quote specific lines from the chat (e.g. "she replied 'ok' / 'yeah' — all one-word answers") to ground your analysis. Always end with actionable next step. **Important: if items 4-8 above apply, pick the most important 1-2 — don't list them all.**
- issues: Point out problems if any (≤25 words each), factual but not too serious. Prioritize issues from items 4-8.
- risks: Flag what might go wrong if this continues, but in a "hey so here's the thing" tone, not a warning
- reply_suggestions: Three styles of replies (≤3 sentences each). Must actually respond to what they just said, not robotic. Note: replies should "open doors" not "close them" — give them something to respond to.
- timing_advice: Give concrete advice like "They're sharing feelings right now — acknowledge that before changing the subject" or "Don't reply, let them come to you."

Tone: Casual, natural, slightly cheeky, but on point. Not like an elder giving advice — like a friend who's roasting you with love.

Strictly prohibited:
- Judging whether someone has feelings for the user
- PUA or emotional manipulation
- Fabricating facts not in the chat
- Templated clichés like "wishing you the best"
- Making decisions for the user
- Creating anxiety or fear

Output pure JSON only, do NOT wrap in markdown code blocks."""

# ── Static few-shot examples (compact, quality reference only) ──

_FEWSHOT_ZH = """=== Few-Shot 质量参考 ===

示例1：
输入：他: 今天加班好累啊 / 我: 辛苦了，晚饭吃了吗 / 他: 还没，准备点外卖 / 我: 我也没吃，一起点？
输出：{"chat_status":"积极互动","analysis":"哎不错诶，这一段聊得挺自然的。你看他主动跟你说'今天加班好累啊'——这说明啥？他没把你当外人，愿意跟你分享当下的状态，这是个好信号。然后你接得也挺顺的：先关心了一句'辛苦了'，再顺势问'一起点？'，从吐槽到约饭一步到位，节奏很舒服。而且他说'准备点外卖'而不是'先忙了回头聊'——说明他没想结束对话诶，这扇门还开着呢。所以你现在就该趁热回他，别让气氛凉了——他还没吃饭呢，正等着你推荐吃啥。","issues":[],"risks":[],"reply_suggestions":{"natural":"你想吃啥？我可以推荐几家附近的","humorous":"外卖小哥又要奔波了哈哈，快点点吧","mature":"先填饱肚子，其他事等会再聊"},"timing_advice":"趁热打铁，现在回。他还没吃饭又愿意跟你聊——这时候你的消息大概率秒读。"}

示例2：
输入：我: 周末有什么安排吗 / 他: 没有 / 我: 最近有部电影还不错 / 他: 哦 / 我: 你喜欢看电影吗 / 他: 还行
输出：{"chat_status":"偏冷淡","analysis":"嘶，这段看得我有点替你着急。你连问了三个问题——周末干嘛、看电影吗、你喜欢电影吗——但她回的分别是'没有''哦''还行'。三句话加一起不到5个字诶！而且完全没有把话题抛回来给你，比如'你呢'或者'你说的什么电影'之类的。这不是她今天累了，这就是不太想聊的表现。但话说回来，你这边也有点问题——噼里啪啦三个问号砸过去，像在面试不是在聊天，换谁都压力山大。所以听我的，现在就打住别发了——她已经给了三次信号，再发就是硬聊了。过一两天换个轻松的话题，而且别用问句开头，用陈述句给她留接话的余地。","issues":["连环追问给对方压力","对方三次极短回复，当下兴趣不高","提问方式像面试，可以更轻松"],"risks":["再追问可能就要被划入'烦人'名单了"],"reply_suggestions":{"natural":"好的，那你先忙，有空再聊","humorous":"今天不太在状态哦哈哈，没事改天","mature":"行，不打扰了，想聊了找我"},"timing_advice":"别回了现在。她已经用三个字给了你三次暗示，再发就是硬聊了。等她自己来找你吧——或者过两天换个轻松的话题，别用问句开场，用陈述句比如'周末看了部还不错的电影'，给她个自然接话的机会。"}

示例3（解题模式+收口信号）：
输入：她: 今天跟同事吵架了好烦 / 我: 为什么吵架，你跟我说说 / 她: 就是工作分配的事，她觉得我抢了她的活 / 我: 你可以跟领导反映一下，这种问题早解决比较好 / 她: 算了不说了 / 我: 好的知道了
输出：{"chat_status":"偏冷淡","analysis":"典型的解题思维翻车现场。她第一句'好烦'是求安慰，你回的是给方案——频道完全没对上。最后那句'好的知道了'更狠，四个字把对话焊死，前面她'算了不说了'已经是放弃信号了。全程你一次反问都没有，一直在诊断问题→给方案，但她要的不是聪明是懂。所以现在别回了，过一两天换个方式——别问那个事了，问她'你还好吗'，共情比方案有用一百倍。","issues":["对方倾诉情绪时用户给方案而非共情","'好的知道了'硬收口，无接话空间","全程零反问，单方面终结对话"],"risks":["继续解题模式会让她下次不想跟你分享烦心事了"],"reply_suggestions":{"natural":"那天的事后来怎么样了，你还好吗","humorous":"跟同事吵架真的太烦了，需要我帮你骂她两句吗","mature":"听起来确实不舒服，想聊的话我一直在"},"timing_advice":"现在别回。等一两天再问，但别问事——问她的感受。"}
=="""

_FEWSHOT_EN = """=== Few-Shot Quality Reference ===

Example 1:
Input: him: worked overtime today, so tired / me: that's rough, did you eat dinner / him: not yet, gonna order takeout / me: me neither, order together?
Output: {"chat_status":"engaged","analysis":"Okay this is actually nice. He opened up to you about work stress — that's not just small talk, he's letting you into his day, which means he's comfortable with you. And your response? Smooth. You acknowledged his mood ('that's rough') then pivoted naturally into making a plan ('order together?'). That transition from venting to action didn't feel forced at all. Here's the kicker: he said 'gonna order takeout' — not 'gotta go' or 'talk later.' He's not trying to end this conversation. The door's open. So here's what you do: reply right now while it's warm. He's hungry and engaged — strike while the iron's hot.","issues":[],"risks":[],"reply_suggestions":{"natural":"What are you in the mood for? I can recommend nearby","humorous":"The delivery guy's about to get busy haha, order quick","mature":"Let's eat first, other things can wait"},"timing_advice":"Reply now. He's hungry and still engaged — your message is gonna land at the perfect moment."}

Example 2:
Input: me: any plans for the weekend / her: nope / me: there's a good movie / her: oh / me: do you like movies / her: kinda
Output: {"chat_status":"cold","analysis":"Oof, okay let me be real with you — this conversation is not vibing. Three replies from her: 'nope,' 'oh,' 'kinda.' That's five words total, zero curiosity about you, zero effort to keep things going. She didn't even throw you a 'you?' or 'what movie?' Nothing. She's either not in a chatting mood at all or just not feeling this conversation. And hey, I gotta say — firing three questions in a row is a lot. It reads more like a job interview than a casual chat. So here's the move: stop sending messages right now. She's given you three signals already — you've read the room, that's enough. Try her again in a couple days, but don't lead with a question this time. Lead with a statement so she has something to naturally bounce off of.","issues":["Three questions in a row = interview vibes","She's giving one-word replies — interest is low rn","Your approach could be more casual, less Q&A"],"risks":["Keep pushing and she'll probably mentally check out completely"],"reply_suggestions":{"natural":"Alright, you seem busy — catch up another time","humorous":"Not your day today huh, no worries","mature":"Understood, I'll let you go. Hit me up when you're free"},"timing_advice":"Don't reply. She sent you three signals already — you read them, that's enough. Let her come back to you. Or try again in a couple days with something light, and don't lead with a question this time. Lead with a statement so she has something to bounce off of."}

Example 3 (Solution Mode + Closing Signals):
Input: she: ugh, had a fight with my coworker today / me: what happened, tell me about it / she: it's about task assignments, she thinks I took her work / me: you should talk to your manager, better to address these things early / she: never mind let's drop it / me: ok got it
Output: {"chat_status":"cold","analysis":"Classic engineer brain in action. Her 'ugh, had a fight' was asking for empathy — you responded with a bug report diagnostic. 'Never mind' was her giving up, and 'ok got it' welded the conversation shut. Zero follow-up questions in the whole exchange. She wanted to be heard, not fixed. Don't reply now — give it a day, then ask how she's doing, not what happened. Empathy > solutions every single time.","issues":["Offering solutions when she needed empathy","'ok got it' is a hard door-close, no next step","Zero follow-up questions — one-directional exchange"],"risks":["She'll stop sharing frustrations if you keep solving instead of listening"],"reply_suggestions":{"natural":"Hey, how have you been — that work stuff still bothering you?","humorous":"Coworker drama is the worst. Need me to come yell at her for you?","mature":"That sounds genuinely frustrating. I'm here if you want to talk."},"timing_advice":"Don't reply now. Wait a day, then ask how she's feeling — not what happened."}
=="""



# ── Relationship-specific prompt additions ──

RELATIONSHIP_PROMPTS = {
    "romantic": (
        "场景：恋爱/暧昧关系。\n"
        "关注点：\n"
        "- 她有没有主动分享自己的日常？主动分享=对你有分享欲\n"
        "- 回复是变快了还是变慢了？突然的变化通常有原因\n"
        "- 有没有用表情、语气词？这些往往比文字本身更诚实\n"
        "- ⚠️ 解题模式：你是不是一直在分析她的问题而不是感受她的情绪？她需要的是懂不是聪明\n"
        '- ⚠️ 收口检测：你的回复是在"开门"还是"关门"？每句都收尾=每次都得她重新找话题\n'
        "- ⚠️ 安全区：话题是不是一直飘在表面（吃了没/干嘛呢）？有没有稍微深入一点的内容\n"
        "节奏感：刚认识别太频繁（隔一两天聊一次更自然），暧昧期可以适度推进但别急，恋爱了记得关注她的情绪需要\n"
        "禁止：绝对判断（'她喜欢你'/'她不喜欢你'）、情感操控、过度解读"
    ),
    "friend": (
        "场景：朋友关系。\n"
        "关注点：\n"
        "- 是你一直在主动找话题，还是对方也会找你？单方面太辛苦就不是健康的朋友关系\n"
        "- 有没有'嗯/哦/好的'这种敷衍三连？偶尔一次正常，连续出现就得注意了\n"
        "- 你们聊的是表面话还是真正想聊的话题？能聊内心深处的事=关系近\n"
        "- ⚠️ 零提问检测：最近几轮谁在问问题？如果都没问，关系在冷却\n"
        "- ⚠️ 表情包接力：对话是不是变成了斗图大赛？表情包安全但不说事\n"
        "注意：朋友间冷淡不一定有问题，可能各自在忙。别把朋友互动当暧昧来分析。\n"
        "禁止：恋爱化解读、过度分析"
    ),
    "family": (
        "场景：家人关系。\n"
        "关注点：\n"
        "- 对话里谁在指责、谁在表达感受？表达感受比指责更能解决问题\n"
        "- 有没有'算了不说了'这种话？这往往意味着情绪已经积压很久了\n"
        "- 父母那一辈和我们的沟通方式本来就不一样，别用自己的标准去要求对方\n"
        "- ⚠️ 解题模式：家人抱怨时你是不是下意识给方案？有时候他们只是想说说话\n"
        "原则：帮你理解双方，而不是站队。缓和矛盾，不是激化。\n"
        "禁止：心理诊断、立场偏袒、火上浇油"
    ),
    "coworker": (
        "场景：同事/职场关系。\n"
        "关注点：\n"
        "- 沟通够不够专业？职场里过度情绪化容易吃亏\n"
        "- 有没有越界的私人话题？保持适当的职场边界感\n"
        "- 话说清楚了没有？职场沟通最重要的是信息准确\n"
        '- ⚠️ 收口/开门：职场消息有没有留"下一步"——对方知道接下来该干嘛吗\n'
        "回复原则：简洁、专业、别给人留把柄\n"
        "禁止：情绪化建议、办公室政治、越界行为建议"
    ),
    "other": (
        "场景：一般社交关系。\n"
        "保持中立，就事论事，别预设你们是什么关系。\n"
        "关注：互相尊重、有没有边界感、互动是不是舒服\n"
        "- ⚠️ 可接话度：你的消息有没有给别人留接话的入口\n"
        "禁止：乱猜关系、过度解读"
    ),
}


SCREENSHOT_EXTRACT_PROMPT = """你是一个聊天截图文字提取助手。从聊天截图中提取所有可见的聊天消息，包括文字和图片内容。

要求：
1. 按时间顺序提取每条消息
2. 区分发言人：对方用"他/她:"，用户自己用"我:"标注
3. 如果聊天中包含图片（如照片、表情包、贴图），请识别图片中的主要物体/场景并描述，格式为 [图片：简短描述]。例如：
   - 对方发了一张火锅照片 → 他/她: [图片：一桌火锅，有毛肚和牛肉]
   - 对方发了一张自拍 → 他/她: [图片：自拍，在咖啡馆里微笑]
   - 对方发了一个猫的表情包 → 他/她: [图片：一只橘猫表情包，配文'不想上班']
4. 对于纯文字消息，直接提取文字内容
5. 对于有文字的表情符号如 [笑哭]，保留文字描述
6. 忽略系统提示（如"对方正在输入"、时间戳等）

目的：保证聊天完整性，让后续分析能理解图中传达的信息。

输出格式：
他/她: 消息内容1
我: 消息内容2
他/她: [图片：一盘寿司]
我: 看起来很好吃！
他/她: 对呀对呀，这家超赞
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
            timeout=httpx.Timeout(60.0, connect=8.0),
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
                    timeout=45.0,  # Per-model timeout (increased for enhanced prompts)
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
        from PIL import Image
        import io as io_module

        t_total = time.time()

        # ── Compress image before encoding (reduce payload + API latency) ──
        # Only compress large images; skip small ones to avoid unnecessary overhead
        t0 = time.time()
        original_size = len(image_bytes)
        compress_threshold = 300 * 1024  # 300KB — only compress images above this
        if original_size > compress_threshold:
            try:
                img = Image.open(io_module.BytesIO(image_bytes))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # Resize if larger than 1200px on either axis
                max_dim = 1200
                if img.width > max_dim or img.height > max_dim:
                    ratio = max_dim / max(img.width, img.height)
                    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
                # Save as JPEG (much smaller than PNG for screenshots)
                buf = io_module.BytesIO()
                img.save(buf, format="JPEG", quality=85, optimize=True)
                compressed = buf.getvalue()
                t_compress = time.time() - t0
                logger.info(
                    f"Image compressed: {original_size}B → {len(compressed)}B "
                    f"({len(compressed)/max(original_size,1)*100:.0f}%) in {t_compress:.2f}s"
                )
                image_bytes = compressed
                content_type = "image/jpeg"
            except Exception as e:
                logger.info(f"Image compression skipped (error): {e}")
        else:
            logger.info(f"Image compression skipped: {original_size}B below {compress_threshold}B threshold")

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
        user_questions = sum(1 for m in user_msgs if '?' in m or '？' in m or '吗' in m or '呢' in m)
        other_question_ratio = round(other_questions / max(len(other_msgs), 1) * 100, 1)
        user_question_ratio = round(user_questions / max(len(user_msgs), 1) * 100, 1)

        # --- NEW: Solution-mode detection ---
        # Check if user messages are heavy on "solving" language (你可以/你应该/其实你/我觉得你)
        solution_phrases = ['你可以', '你应该', '其实你', '我觉得你', '建议你', '你最好',
                            '我帮你分析', '问题在于', '解决方案', '试试看', '为什么不']
        user_solution_count = sum(1 for m in user_msgs if any(p in m for p in solution_phrases))
        user_solution_ratio = round(user_solution_count / max(len(user_msgs), 1) * 100, 1)

        # --- NEW: Closing-signal detection ---
        # Messages that terminate a conversation thread
        closing_words = ['好的', '知道了', '嗯嗯', '明白了', '收到', '行', 'OK', 'ok', '好嘞', '哦哦']
        user_closing_count = sum(
            1 for m in user_msgs
            if len(_strip_prefix(m)) <= 6 and any(w in _strip_prefix(m) for w in closing_words)
        )
        user_closing_ratio = round(user_closing_count / max(len(user_msgs), 1) * 100, 1)

        # --- NEW: Safe-zone detection ---
        # Check if topics are all neutral/surface-level (no personal sharing, no curiosity)
        safe_zone_indicators = ['天气', '吃了', '上班', '加班', '忙', '累', '还好', '还行',
                                '工作', '学习', '作业', '开会', '路上', '堵车']
        safe_zone_count = sum(
            1 for m in (user_msgs + other_msgs)
            if any(w in _strip_prefix(m) for w in safe_zone_indicators)
        )
        safe_zone_ratio = round(safe_zone_count / max(len(user_msgs) + len(other_msgs), 1) * 100, 1)

        # --- NEW: Emoji dependency (pure emoji/sticker relay) ---
        # Count consecutive rounds where both sides only sent emoji/short-form
        def _is_pure_emoji(msg: str) -> bool:
            stripped = _strip_prefix(msg)
            if not stripped:
                return False
            emojis_in_msg = emoji_pattern.findall(stripped)
            emoji_chars = ''.join(emojis_in_msg)
            # If >70% of the message content is emoji characters (after removing text)
            text_without_emoji = stripped
            for e in emojis_in_msg:
                text_without_emoji = text_without_emoji.replace(e, '')
            return len(text_without_emoji.strip()) <= 2 and len(emojis_in_msg) >= 1

        # Count consecutive emoji-only rounds
        emoji_relay_count = 0
        max_emoji_relay = 0
        all_msgs_ordered = sorted(
            [(i, m) for i, m in enumerate(lines)],
            key=lambda x: x[0]
        )
        for _, msg in all_msgs_ordered:
            if _is_pure_emoji(msg):
                emoji_relay_count += 1
                max_emoji_relay = max(max_emoji_relay, emoji_relay_count)
            else:
                # Allow one short-word message to still count as relay continuation
                stripped = _strip_prefix(msg)
                if len(stripped) <= 3 and emoji_relay_count > 0:
                    emoji_relay_count += 1
                    max_emoji_relay = max(max_emoji_relay, emoji_relay_count)
                else:
                    emoji_relay_count = 0

        # --- Notable patterns (enhanced with new dimensions) ---
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

        # NEW patterns from the enhanced analysis dimensions:
        # Zero questions alert
        if other_question_ratio == 0 and user_question_ratio == 0 and len(other_msgs) >= 3:
            patterns.append("⚠️零提问警报：双方最近几轮都没有互问问题，都在等对方先伸手")
        elif other_question_ratio == 0 and len(other_msgs) >= 3:
            patterns.append("对方零提问——没有把话题抛回来，对话由用户单方面驱动")
        elif user_question_ratio == 0 and len(user_msgs) >= 3:
            patterns.append("用户零提问——你一直在说自己的，没问过对方任何事")

        # Solution mode warning
        if user_solution_ratio >= 50 and len(user_msgs) >= 2:
            patterns.append(f"⚠️解题模式：用户{user_solution_ratio}%的回复在给建议/方案(你可以/你应该/其实你)，对方可能只是倾诉")

        # Closing signal (door-closing)
        if user_closing_ratio >= 40 and len(user_msgs) >= 3:
            patterns.append(f"收口信号：用户{user_closing_ratio}%回复是'好的/知道了/嗯嗯'类关门语，每次都在结束话题而非延展")

        # Safe zone (flat conversation)
        if safe_zone_ratio >= 60 and len(user_msgs) + len(other_msgs) >= 6:
            patterns.append(f"安全区对话：{safe_zone_ratio}%内容停留在天气/工作/吃了没等表面话题，缺乏推进力")

        # Emoji dependency
        if max_emoji_relay >= 3:
            patterns.append(f"表情包接力：连续{max_emoji_relay}轮以上纯表情/极短回复，表面没断但实际没交流")

        # Conversation rhythm mismatch
        if user_msgs and other_msgs and len(user_msgs) >= len(other_msgs) * 2 and len(other_msgs) >= 2:
            patterns.append("节奏不匹配：用户发消息频率远高于对方，可能节奏没对齐")

        return {
            'total_messages': len(lines),
            'total_rounds': max(len(user_msgs), len(other_msgs)),
            'user_msgs': len(user_msgs),
            'other_msgs': len(other_msgs),
            'avg_user_len': avg_user_len,
            'avg_other_len': avg_other_len,
            'other_question_ratio': other_question_ratio,
            'user_question_ratio': user_question_ratio,
            'other_emoji_count': other_emoji_count,
            'user_emoji_count': user_emoji_count,
            'other_short_ratio': other_short_ratio,
            'sentiment_pos': pos_count,
            'sentiment_neg': neg_count,
            'topic_coherence': topic_coherence,
            'user_solution_ratio': user_solution_ratio,
            'user_closing_ratio': user_closing_ratio,
            'safe_zone_ratio': safe_zone_ratio,
            'max_emoji_relay': max_emoji_relay,
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
                        f", 解题模式{case.get('user_solution_ratio', 0)}%"
                        f", 收口{case.get('user_closing_ratio', 0)}%"
                        f", 安全区{case.get('safe_zone_ratio', 0)}%"
                        f", 表情接力{case.get('max_emoji_relay', 0)}轮"
                    )
                else:
                    sentiment_info = (
                        f", emoji {case.get('other_emoji_count', 0)}"
                        f", short-reply {case.get('other_short_ratio', 0)}%"
                        f", sentiment pos/neg {case.get('sentiment_pos', 0)}/{case.get('sentiment_neg', 0)}"
                        f", coherence {case.get('topic_coherence', 0)}%"
                        f", solution {case.get('user_solution_ratio', 0)}%"
                        f", closing {case.get('user_closing_ratio', 0)}%"
                        f", safe-zone {case.get('safe_zone_ratio', 0)}%"
                        f", emoji-relay {case.get('max_emoji_relay', 0)}rds"
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
        fewshot_dynamic = ""  # Disabled to keep prompt lean (static examples sufficient)

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

        # Deep signal line (new dimensions)
        deep_signal_line = (
            f"Deep signals: solution-mode={features['user_solution_ratio']}%, "
            f"closing={features['user_closing_ratio']}%, safe-zone={features['safe_zone_ratio']}%, "
            f"emoji-relay={features['max_emoji_relay']}rds, Q%=user{features['user_question_ratio']}/other{features['other_question_ratio']}"
            if language == "en" else
            f"深层信号: 解题模式{features['user_solution_ratio']}%, "
            f"收口{features['user_closing_ratio']}%, 安全区{features['safe_zone_ratio']}%, "
            f"表情接力{features['max_emoji_relay']}轮, 问句比=用户{features['user_question_ratio']}/对方{features['other_question_ratio']}%"
        )

        if language == "en":
            return f"""{relationship_extra}

{fewshot_static}
{fewshot_dynamic}
Chat ({features['total_messages']} messages, ~{features['total_rounds']} rounds):
---
{chat_content}
---

Quick stats: other {features['other_msgs']}msgs(avg{features['avg_other_len']}c,{features['other_short_ratio']}%short), user {features['user_msgs']}msgs(avg{features['avg_user_len']}c)
{deep_signal_line}
{emoji_line}, {sentiment_line}
Patterns: {features['notable_patterns']}

As a perceptive friend, analyze this conversation. Output JSON only."""
        return f"""{relationship_extra}

{fewshot_static}
{fewshot_dynamic}
聊天记录（{features['total_messages']}条/{features['total_rounds']}轮）：
---
{chat_content}
---

快速参考：对方{features['other_msgs']}条（均长{features['avg_other_len']}字,{features['other_short_ratio']}%短回复），用户{features['user_msgs']}条（均长{features['avg_user_len']}字）
{deep_signal_line}
{emoji_line}，{sentiment_line}
模式：{features['notable_patterns']}

以一个懂你的朋友身份，分析这段对话。输出纯JSON。"""

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
        generic_zh = ["祝你们越来越好", "祝你好运"]
        generic_en = ["keep it up", "good luck", "wishing you the best"]
        generic = generic_zh if zh else generic_en
        for phrase in generic:
            if phrase.lower() in analysis_str:
                warnings.append(f"Generic phrase in analysis: '{phrase}'")

        # Check 2: Does analysis reference the chat content? (relaxed for conversational style)
        # Look for quoted text, specific word counts, or descriptive references
        has_quote = any(c in str(analysis) for c in ['"', '"', '「', '」', "'", '、'])
        has_specific_ref = (
            ('条' in str(analysis) and any(c.isdigit() for c in str(analysis)))
            or ('次' in str(analysis) and any(c.isdigit() for c in str(analysis)))
            or ('句' in str(analysis) and any(c.isdigit() for c in str(analysis)))
            or ('轮' in str(analysis))
            or ('个字' in str(analysis))
            or ('不到' in str(analysis) and '字' in str(analysis))
        ) if zh else (
            ('reply' in analysis_str or 'word' in analysis_str)
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

        # Check 5 (NEW): Analysis mentions relevant deep-signal keywords when issues are present
        issues = data.get("issues", [])
        if isinstance(issues, str):
            issues = [issues]
        if isinstance(issues, list) and len(issues) > 0:
            issues_text = " ".join(str(i) for i in issues).lower() if zh else " ".join(str(i) for i in issues).lower()
            analysis_text = str(analysis).lower()

            # Solution mode detected but not in analysis
            solution_keywords = ["解题", "给方案", "给建议", "solution", "advice", "fixing"] if zh else ["solution", "advice", "fixing", "solving"]
            if any(k in issues_text for k in solution_keywords) and not any(k in analysis_text for k in solution_keywords):
                warnings.append("Issues mention solution-mode but analysis doesn't address it")

            # Closing signals detected but not in analysis
            closing_keywords = ["收口", "关门", "closing"] if zh else ["closing", "door"]
            if any(k in issues_text for k in closing_keywords) and not any(k in analysis_text for k in closing_keywords):
                warnings.append("Issues mention closing-signals but analysis doesn't address it")

            # Zero questions detected but not in analysis
            q_keywords = ["提问", "反问", "question"] if zh else ["question"]
            if any(k in issues_text for k in q_keywords) and not any(k in analysis_text for k in q_keywords):
                warnings.append("Issues mention zero-questions but analysis doesn't address it")

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
        raw_status_str = str(raw_status).strip()

        # Exact match first
        chat_status = status_map.get(
            raw_status_str.lower() if language == "en" else raw_status_str
        )
        # Fuzzy match: AI may append extra text like "偏冷淡，互动性弱"
        if chat_status is None:
            for key, value in status_map.items():
                if key in raw_status_str:
                    chat_status = value
                    break
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
