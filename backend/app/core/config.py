import os
from dotenv import load_dotenv

# override=True 确保 .env 文件值覆盖系统环境变量
load_dotenv(override=True)


def _parse_model_list(env_key: str, fallback: str) -> list[str]:
    """Parse comma-separated model list from env, fallback to single model."""
    value = os.getenv(env_key, "").strip()
    if value:
        return [m.strip() for m in value.split(",") if m.strip()]
    # Fallback: use the single-model env key for backward compatibility
    single = os.getenv(env_key.replace("_MODELS", "_MODEL"), fallback).strip()
    return [single] if single else []


class Settings:
    # ── 通用 ──
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

    # ── 模型（支持多个，逗号分隔，按优先级排序） ──
    TEXT_MODELS: list[str] = _parse_model_list("TEXT_MODELS", "doubao-seed-1-8-251228")
    VISION_MODELS: list[str] = _parse_model_list("VISION_MODELS", "doubao-vision-pro-32k")

    # ── 向后兼容：仍支持单一 OPENAI_MODEL / VISION_MODEL ──
    # （如果 TEXT_MODELS 未设置，会自动从 OPENAI_MODEL 读取）

    # ── 请求参数 ──
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "400"))
    VISION_TEMPERATURE: float = float(os.getenv("VISION_TEMPERATURE", "0.3"))
    VISION_MAX_TOKENS: int = int(os.getenv("VISION_MAX_TOKENS", "2000"))

    # ── 限流 ──
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW: int = 60

    # ── 每日使用限额（免费用户，文字分析和截图上传共享同一配额） ──
    FREE_DAILY_LIMIT: int = int(os.getenv("FREE_DAILY_LIMIT", "3"))

    # ── 内容校验（可通过 .env 配置） ──
    MAX_CHAT_LENGTH: int = int(os.getenv("MAX_CHAT_LENGTH", "2000"))
    MIN_CHAT_LENGTH: int = int(os.getenv("MIN_CHAT_LENGTH", "10"))
    MAX_SCREENSHOT_SIZE: int = 10 * 1024 * 1024
    MAX_SCREENSHOTS_PER_REQUEST: int = int(os.getenv("MAX_SCREENSHOTS_PER_REQUEST", "3"))
    ALLOWED_IMAGE_TYPES: set = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

    # ── 告警 ──
    ALERT_WEBHOOK_URL: str = os.getenv("ALERT_WEBHOOK_URL", "")
    PUSHPLUS_TOKEN: str = os.getenv("PUSHPLUS_TOKEN", "")
    # 告警冷却时间（秒），同类型告警在此时间内不重复发送
    ALERT_COOLDOWN_SECONDS: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "1800"))

    # ── 分享奖励（V1.2） ──
    ENABLE_SHARE_REWARD: bool = os.getenv("ENABLE_SHARE_REWARD", "false").lower() == "true"
    MAX_SHARE_REWARDS_PER_DAY: int = int(os.getenv("MAX_SHARE_REWARDS_PER_DAY", "2"))


settings = Settings()
