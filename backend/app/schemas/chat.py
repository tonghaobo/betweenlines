from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class ChatStatus(str, Enum):
    POSITIVE = "积极互动"
    NORMAL = "普通互动"
    POLITE = "礼貌回应"
    COLD = "偏冷淡"
    HIGH_RISK = "对话风险较高"


class ReplyStyle(str, Enum):
    NATURAL = "natural"
    HUMOROUS = "humorous"
    MATURE = "mature"


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


class ScreenshotAnalysisResponse(BaseModel):
    """截图上传后先返回提取的文字，供用户确认后再分析"""
    extracted_text: str = Field(..., description="从截图中提取的聊天文字")
    image_preview: Optional[str] = Field(None, description="压缩后的预览图base64（可选）")


# 响应 Schema
class ReplySuggestions(BaseModel):
    natural: str = Field(..., description="自然版回复")
    humorous: str = Field(..., description="幽默版回复")
    mature: str = Field(..., description="成熟版回复")


class ChatAnalysisResponse(BaseModel):
    chat_status: ChatStatus = Field(..., description="当前互动状态")
    analysis: str = Field(..., description="互动分析描述")
    issues: List[str] = Field(default_factory=list, description="发现的聊天问题")
    risks: List[str] = Field(default_factory=list, description="风险提醒")
    reply_suggestions: ReplySuggestions = Field(..., description="回复建议")
    timing_advice: str = Field(..., description="节奏建议")


class FeedbackRequest(BaseModel):
    analysis_id: Optional[str] = Field(None, description="分析记录ID")
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
    helpful_rate: float = 0
    reply_adoption_rate: float = 0
    analysis_count_per_user: float = 0
    avg_analysis_duration_ms: int = 0
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
