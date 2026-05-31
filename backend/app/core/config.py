import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "doubao-pro-32k")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW: int = 60

    MAX_CHAT_LENGTH: int = 5000
    MIN_CHAT_LENGTH: int = 10


settings = Settings()
