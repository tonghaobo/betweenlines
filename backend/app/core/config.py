import os
from dotenv import load_dotenv

# override=True 确保 .env 文件值覆盖系统环境变量
load_dotenv(override=True)


class Settings:
    # ── 通用 ──
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

    # ── 模型 ──
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "doubao-seed-1-8-251228")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "doubao-vision-pro-32k")

    # ── 请求参数 ──
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1000"))
    VISION_TEMPERATURE: float = float(os.getenv("VISION_TEMPERATURE", "0.3"))
    VISION_MAX_TOKENS: int = int(os.getenv("VISION_MAX_TOKENS", "2000"))

    # ── 限流 ──
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW: int = 60

    # ── 内容校验 ──
    MAX_CHAT_LENGTH: int = 5000
    MIN_CHAT_LENGTH: int = 10
    MAX_SCREENSHOT_SIZE: int = 10 * 1024 * 1024
    ALLOWED_IMAGE_TYPES: set = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


settings = Settings()
