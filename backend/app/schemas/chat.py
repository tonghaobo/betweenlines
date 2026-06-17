from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class ChatStatus(str, Enum):
    POSITIVE = "积极互动"
    NORMAL = "普通互动"
    POLITE = "礼貌回应"
    COLD = "偏冷淡"
    HIGH_RISK = "对话风险较高"


RiskLevel = Literal["low", "medium", "high"]


class TurningPoint(BaseModel):
    """聊天拐点检测结果"""
    detected: bool = Field(..., description="是否检测到拐点")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0~1")
    message_index: Optional[int] = Field(None, description="拐点消息序号")
    quoted_message: Optional[str] = Field(None, description="拐点处的引用消息")
    signals: list[str] = Field(default_factory=list, description="检测到的信号标签")
    explanation: str = Field("", description="拐点原因解释")
    risk_level: RiskLevel = Field("low", description="风险等级: low/medium/high")


class ReplyStyle(str, Enum):
    NATURAL = "natural"
    HUMOROUS = "humorous"
    MATURE = "mature"


TrendType = Literal["warm_up", "stable", "cool_down", "conversation_end"]
ConfidenceLevel = Literal["low", "medium", "high"]


class TrajectoryPrediction(BaseModel):
    """对话走势预测——每条回复建议的可能走向"""
    trend: TrendType = Field(..., description="走势类型: warm_up/stable/cool_down/conversation_end")
    confidence: ConfidenceLevel = Field("medium", description="置信度: low/medium/high")
    risk_level: RiskLevel = Field("low", description="风险等级: low/medium/high")
    explanation: str = Field("", description="走势原因解释")


class ReplySuggestion(BaseModel):
    """单条回复建议，包含走势预测"""
    reply: str = Field(..., description="回复文本")
    trajectory: TrajectoryPrediction = Field(..., description="走势预测")


RelationshipType = Literal["romantic", "friend", "family", "coworker", "other"]


# 请求 Schema
class ChatAnalysisRequest(BaseModel):
    chat_content: str = Field(
        ..., 
        min_length=1, 
        description="用户粘贴的聊天记录，支持微信格式"
    )
    relationship_type: RelationshipType = Field(
        "romantic",
        description="关系类型: romantic, friend, family, coworker, other"
    )
    anonymous_user_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="客户端生成的匿名用户ID (cc_xxxxx 格式)",
    )
    source: Optional[str] = Field(
        None,
        description="来源标识：'screenshot' 表示截图提取的文字，此时不消耗文字分析配额",
    )
    language: Optional[str] = Field(
        "zh",
        description="输出语言：'zh' 中文 / 'en' 英文",
    )


class ScreenshotAnalysisResponse(BaseModel):
    """截图上传后先返回提取的文字，供用户确认后再分析"""
    extracted_text: str = Field(..., description="从截图中提取的聊天文字")
    image_preview: Optional[str] = Field(None, description="压缩后的预览图base64（可选）")


# 响应 Schema
class ReplySuggestions(BaseModel):
    natural: ReplySuggestion = Field(..., description="自然版回复+走势")
    humorous: ReplySuggestion = Field(..., description="幽默版回复+走势")
    mature: ReplySuggestion = Field(..., description="成熟版回复+走势")


class ChatAnalysisResponse(BaseModel):
    analysis_id: Optional[int] = Field(None, description="分析记录ID，用于复盘关联")
    chat_status: ChatStatus = Field(..., description="当前互动状态")
    analysis: str = Field(..., description="互动分析描述")
    issues: List[str] = Field(default_factory=list, description="发现的聊天问题")
    risks: List[str] = Field(default_factory=list, description="风险提醒")
    reply_suggestions: ReplySuggestions = Field(..., description="回复建议")
    timing_advice: str = Field(..., description="节奏建议")
    turning_point: TurningPoint = Field(..., description="聊天拐点检测结果")


# ── Review (Post-Reply) Schemas ──

ReviewStatus = Literal["improved", "similar", "worsened", "insufficient_data"]

ChangeDirection = Literal["up", "down", "same"]


class ConversationChanges(BaseModel):
    """维度变化——对比上次和本次聊天的变化方向"""
    initiative: ChangeDirection = "same"
    reply_length: ChangeDirection = "same"
    emotional_engagement: ChangeDirection = "same"
    coldness_risk: ChangeDirection = "same"
    topic_continuity: ChangeDirection = "same"


class ReviewRequest(BaseModel):
    analysis_id: int = Field(..., description="上次分析的记录ID")
    new_chat_content: str = Field(..., min_length=1, description="后续聊天内容")
    relationship_type: RelationshipType = Field("romantic", description="关系类型")
    language: Optional[str] = Field("zh", description="输出语言")


class ReviewResponse(BaseModel):
    review_id: Optional[int] = Field(None, description="复盘记录ID")
    review_status: ReviewStatus = Field(..., description="复盘结果: improved/similar/worsened/insufficient_data")
    changes: ConversationChanges = Field(default_factory=ConversationChanges, description="各维度变化方向")
    previous_advice_effectiveness: str = Field("", description="上次建议有效性评估")
    summary: str = Field("", description="复盘总结")
    next_step_advice: str = Field("", description="下一步建议")


class FeedbackRequest(BaseModel):
    analysis_id: Optional[str] = Field(None, description="分析记录ID")
    anonymous_user_id: Optional[str] = Field(None, min_length=3, max_length=64, description="匿名用户ID")
    helpful: bool = Field(..., description="是否有帮助")
    reason: list[str] = Field(default_factory=list, description="反馈原因")
    comment: str = Field("", description="补充文字")


class FeedbackResponse(BaseModel):
    message: str = "感谢你的反馈！"


class OutcomeRequest(BaseModel):
    analysis_id: Optional[str] = Field(None, description="分析记录ID")
    reply_used: str = Field(..., description="回复使用情况: sent/not_sent/modified")
    outcome: str = Field("", description="后续结果: more_positive/about_same/colder/no_reply/prefer_not")


class OutcomeResponse(BaseModel):
    message: str = "感谢你的反馈！"


# ── Analytics schemas ──

class TrackEventRequest(BaseModel):
    anonymous_user_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Anonymous user ID (cc_xxxxx format)",
    )
    event_name: str = Field(
        ...,
        description="Event name: page_view, analysis_created, analysis_success, reply_generated, reply_used, feedback_given, return_visit",
    )
    properties: dict | None = Field(None, description="Event properties")
    session_id: str | None = Field(None, description="Session ID")


class TrackEventResponse(BaseModel):
    success: bool = True


class MetricsResponse(BaseModel):
    dau: int = 0
    d1_retention: float = 0
    d7_retention: float = 0
    total_analyses: int = 0
    total_image_analyses: int = 0
    helpful_rate: float = 0
    reply_adoption_rate: float = 0
    analysis_count_per_user: float = 0
    avg_analysis_duration_ms: int = 0
    avg_ocr_duration_ms: int = 0
    share_conversion_rate: float = 0
    share_clicked_count: int = 0
    share_succeeded_count: int = 0


class UsageResponse(BaseModel):
    analysis_used: int = 0
    analysis_limit: int = 0
    analysis_reward: int = 0
    screenshot_used: int = 0
    screenshot_limit: int = 0
    max_chat_length: int = 5000
    max_screenshots_per_request: int = 3
    share_reward_enabled: bool = False
    max_share_rewards_per_day: int = 0
    share_rewards_used_today: int = 0
    feedback_reward_enabled: bool = False
    max_feedback_rewards_per_day: int = 0
    feedback_rewards_used_today: int = 0


class ShareRewardRequest(BaseModel):
    anonymous_user_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Anonymous user ID (cc_xxxxx format)",
    )
    share_type: str = Field(
        ...,
        description="Share type: share_image, clipboard_image, save_image, share_link",
    )
    share_hash: str = Field(
        ...,
        min_length=8,
        description="Hash of shared content for dedup",
    )


class ShareRewardResponse(BaseModel):
    granted: bool = True
    bonus_count: int = 1
    message: str = "Reward granted!"


# ── Tag schemas (Phase 3) ──

class AnalysisTags(BaseModel):
    conversation_stage: str = ""
    other_style: str = ""
    user_issue: str = ""
    label_source: str = "rule"


class TagStatsResponse(BaseModel):
    total_tagged: int = 0
    conversation_stage_dist: dict[str, int] = Field(default_factory=dict)
    other_style_dist: dict[str, int] = Field(default_factory=dict)
    user_issue_dist: dict[str, int] = Field(default_factory=dict)


# ── Quality dashboard schemas (Phase 4) ──

class ErrorCaseItem(BaseModel):
    id: int
    analysis_id: str = ""
    reason: str = ""
    comment: str = ""
    chat_status: str = ""
    conversation_stage: str = ""
    other_style: str = ""
    user_issue: str = ""
    created_at: str = ""


class ErrorCasesResponse(BaseModel):
    cases: list[ErrorCaseItem] = Field(default_factory=list)
    total: int = 0


class ErrorCaseStatsResponse(BaseModel):
    total_errors: int = 0
    reason_distribution: dict[str, int] = Field(default_factory=dict)
    stage_error_distribution: dict[str, int] = Field(default_factory=dict)
