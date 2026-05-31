# Day 5-6：后端 API 与 AI 集成

## 任务概述
完成 FastAPI 后端的核心业务逻辑：OpenAI 集成、System Prompt 构建、JSON 结构化输出、错误处理、速率限制。

**工作量：2 天**

---

## Day 5（上午）：OpenAI 服务层开发

### 任务 5.1：创建 OpenAI 服务

创建 `backend/app/services/openai_service.py`：

```python
import json
import logging
from typing import Optional
from openai import AsyncOpenAI
from app.schemas.chat import ChatAnalysisResponse, ReplySuggestions, ChatStatus

logger = logging.getLogger(__name__)


# System Prompt — 直接来自 PRD
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
严格 JSON。"""


class OpenAIService:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def analyze_chat(self, chat_content: str) -> ChatAnalysisResponse:
        """
        调用 OpenAI 分析聊天记录，返回结构化分析结果。
        """
        user_prompt = self._build_user_prompt(chat_content)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI returned empty response")

            return self._parse_response(content)

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def _build_user_prompt(self, chat_content: str) -> str:
        """
        构建发送给 OpenAI 的用户 Prompt。
        """
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
        """
        解析 OpenAI 返回的 JSON，验证并转换为 Pydantic 模型。
        """
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {raw_json[:200]}")
            raise ValueError(f"Invalid JSON from OpenAI: {str(e)}")

        # 校验并标准化 chat_status
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

        # 构建 ReplySuggestions
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
```

### 任务 5.2：创建配置管理

创建 `backend/app/core/config.py`：

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    
    # 速率限制
    RATE_LIMIT_REQUESTS: int = 20  # 每分钟最大请求数
    RATE_LIMIT_WINDOW: int = 60    # 时间窗口（秒）

    # 聊天分析限制
    MAX_CHAT_LENGTH: int = 5000
    MIN_CHAT_LENGTH: int = 10


settings = Settings()
```

创建 `backend/app/core/__init__.py`（空文件）

---

## Day 5（下午）：API 路由实现

### 任务 5.3：实现分析接口

重写 `backend/app/routers/chat.py`：

```python
import logging
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.chat import (
    ChatAnalysisRequest,
    ChatAnalysisResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.openai_service import OpenAIService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


def get_openai_service() -> OpenAIService:
    """依赖注入：创建 OpenAI 服务实例"""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in .env",
        )
    return OpenAIService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
    )


@router.post("/analyze", response_model=ChatAnalysisResponse)
async def analyze_chat(
    request: ChatAnalysisRequest,
    service: OpenAIService = Depends(get_openai_service),
):
    """
    分析聊天记录，返回互动状态、分析、问题和回复建议。
    
    - **chat_content**: 用户粘贴的聊天记录（10-5000字符）
    """
    # 输入验证
    if len(request.chat_content.strip()) < settings.MIN_CHAT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Chat content must be at least {settings.MIN_CHAT_LENGTH} characters",
        )
    
    if len(request.chat_content) > settings.MAX_CHAT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Chat content must be at most {settings.MAX_CHAT_LENGTH} characters",
        )

    try:
        result = await service.analyze_chat(request.chat_content)
        return result
    except ValueError as e:
        logger.error(f"Value error in analyze: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again later.",
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    收集用户反馈（有帮助/没帮助）。
    V1 阶段仅记录日志，后续接入数据库。
    """
    logger.info(f"Feedback received: helpful={request.helpful}, analysis_id={request.analysis_id}")
    return FeedbackResponse(message="感谢你的反馈！")
```

### 任务 5.4：添加全局异常处理

更新 `backend/app/main.py`，添加异常处理器：

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Chat Coach API",
    description="Chat Coach - AI-powered chat analysis and reply suggestions",
    version="0.1.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/")
async def root():
    return {"message": "Chat Coach API is running", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# 注册路由
from app.routers import chat

app.include_router(chat.router)
```

---

## Day 6（上午）：错误处理与边界情况

### 任务 5.5：添加输入清理工具

创建 `backend/app/services/chat_cleaner.py`：

```python
import re
from typing import List


def clean_chat_content(raw_text: str) -> str:
    """
    清洗用户输入的聊天记录：
    1. 去除首尾空白
    2. 规范化换行
    3. 移除多余空行
    4. 截断过长内容（保留前后各 2500 字符）
    """
    text = raw_text.strip()
    # 规范化换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 移除多余空行（保留单个空行）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def validate_chat_format(text: str) -> List[str]:
    """
    验证聊天记录格式，返回警告列表。
    不阻止分析，仅返回提示。
    """
    warnings = []
    
    # 检查是否有明显的对话格式
    has_speaker_pattern = bool(re.search(r"^[A-Za-z\u4e00-\u9fff]+[：:]", text, re.MULTILINE))
    
    if not has_speaker_pattern:
        warnings.append("未检测到明显的对话格式，分析结果可能不准确。建议使用 'A: xxx' 或 '对方: xxx' 格式。")
    
    # 检查是否过于简短
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        warnings.append("对话轮次过少，建议提供更多上下文。")
    
    return warnings


def is_potentially_harmful(text: str) -> bool:
    """
    检查内容是否可能包含违规内容。
    V1 阶段使用简单的关键词匹配。
    """
    harmful_keywords = [
        "PUA", "pua", "把妹", "泡妞", "搭讪话术",
        "操控", "跟踪", "骚扰", "情色",
    ]
    
    text_lower = text.lower()
    for keyword in harmful_keywords:
        if keyword.lower() in text_lower:
            return True
    return False
```

### 任务 5.6：集成输入清理到路由

更新 `backend/app/routers/chat.py` 的 `analyze_chat` 函数，在开头添加：

```python
from app.services.chat_cleaner import clean_chat_content, validate_chat_format, is_potentially_harmful

# 在 analyze_chat 函数中，request 验证之后、调用 service 之前添加：
    # 检查违规内容
    if is_potentially_harmful(request.chat_content):
        raise HTTPException(
            status_code=400,
            detail="内容包含不适当的请求。本工具仅用于正常社交沟通分析。",
        )
    
    # 清洗内容
    cleaned_content = clean_chat_content(request.chat_content)
    
    # 格式验证（仅记录日志，不阻止）
    warnings = validate_chat_format(cleaned_content)
    if warnings:
        logger.info(f"Chat format warnings: {warnings}")
```

并修改调用为使用 `cleaned_content`：

```python
    try:
        result = await service.analyze_chat(cleaned_content)
        return result
```

---

## Day 6（下午）：速率限制与 API 测试

### 任务 5.7：添加简易速率限制

创建 `backend/app/middleware/rate_limit.py`：

```python
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from app.core.config import settings


class SimpleRateLimiter:
    """
    简易内存速率限制器（V1 版本，不依赖 Redis）。
    每个 IP 每分钟最多 N 次请求。
    """

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        # 清理过期记录
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < self.window_seconds
        ]
        # 检查是否超限
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        # 记录本次请求
        self.requests[client_id].append(now)
        return True


rate_limiter = SimpleRateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
)


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI 中间件：对 /api/v1/analyze 接口进行速率限制。
    """
    if request.url.path == "/api/v1/analyze":
        client_ip = request.client.host if request.client else "unknown"
        
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment before trying again.",
            )
    
    response = await call_next(request)
    return response
```

在 `backend/app/main.py` 中注册中间件：

```python
from app.middleware.rate_limit import rate_limit_middleware

# 在其他 middleware 之后添加
app.middleware("http")(rate_limit_middleware)
```

### 任务 5.8：创建 API 测试脚本

创建 `backend/tests/test_api.py`：

```python
"""
Chat Coach API 测试脚本
使用方法：python tests/test_api.py
前提：后端服务已启动在 http://localhost:8000
"""
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

SAMPLE_CHAT = """A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢
A: 那快去吃点东西吧
B: 嗯嗯好的"""


async def test_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"[Health] Status: {response.status_code}")
        print(f"[Health] Body: {response.json()}")
        assert response.status_code == 200


async def test_analyze():
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": SAMPLE_CHAT},
        )
        print(f"[Analyze] Status: {response.status_code}")
        data = response.json()
        print(f"[Analyze] Status: {data.get('chat_status')}")
        print(f"[Analyze] Analysis: {data.get('analysis', '')[:100]}...")
        print(f"[Analyze] Issues: {data.get('issues')}")
        print(f"[Analyze] Risks: {data.get('risks')}")
        print(f"[Analyze] Natural Reply: {data.get('reply_suggestions', {}).get('natural', '')}")
        print(f"[Analyze] Timing: {data.get('timing_advice')}")
        assert response.status_code == 200
        assert "chat_status" in data
        assert "reply_suggestions" in data


async def test_analyze_empty():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json={"chat_content": "hi"},
        )
        print(f"[Analyze Empty] Status: {response.status_code}")
        assert response.status_code == 400


async def test_feedback():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"helpful": True},
        )
        print(f"[Feedback] Status: {response.status_code}")
        print(f"[Feedback] Body: {response.json()}")
        assert response.status_code == 200


async def main():
    print("=" * 50)
    print("Chat Coach API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Chat Analysis", test_analyze),
        ("Empty Input Validation", test_analyze_empty),
        ("Feedback Submission", test_feedback),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            print(f"\n--- {name} ---")
            await test_fn()
            print(f"✅ {name} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {str(e)}")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
```

创建 `backend/tests/__init__.py`（空文件）

### 任务 5.9：手动测试验证

启动后端后运行测试：

```bash
cd /Users/tonghaobo/codes/chatvibe/backend
pip install httpx
python tests/test_api.py
```

---

## 验收标准（Day 6 结束）

- [ ] OpenAI 服务层可正常调用，返回结构化 JSON
- [ ] `/api/v1/analyze` 接口返回完整的 `ChatAnalysisResponse`
- [ ] System Prompt 严格遵循 PRD 要求（禁止 PUA、不做绝对判断等）
- [ ] 输入清洗：空白字符处理、换行规范化
- [ ] 违规内容检测：PUA 等关键词被拦截
- [ ] 速率限制：同一 IP 短时间内大量请求返回 429
- [ ] 空输入/过短输入返回 400 错误
- [ ] 全局异常处理：未预期错误返回 500 而非崩溃
- [ ] 测试脚本全部通过（需要配置 OPENAI_API_KEY）
- [ ] Swagger UI (`/docs`) 中可正常测试接口

## 给 AI 的执行提示

```
请按照以上步骤，依次完成 Day 5 和 Day 6 的所有任务。
先创建服务层代码（openai_service.py），再实现路由逻辑，最后添加错误处理和测试。
注意：.env 中的 OPENAI_API_KEY 需要填入真实值才能测试 AI 调用。
在测试前，请确认 uvicorn 服务已启动。
如果 OpenAI 调用返回非 JSON 格式，_parse_response 应有容错处理。
```
