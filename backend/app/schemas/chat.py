from pydantic import BaseModel, Field
from typing import List, Optional
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


# 请求 Schema
class ChatAnalysisRequest(BaseModel):
    chat_content: str = Field(
        ..., 
        min_length=10, 
        max_length=5000,
        description="用户粘贴的聊天记录，支持微信格式"
    )


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


class FeedbackResponse(BaseModel):
    message: str = "感谢你的反馈！"
