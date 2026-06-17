import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 确保 .env 在任何 os.getenv 之前加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BetweenLines API...")
    try:
        from app.services.storage import init_db
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init skipped: {e}")

    # Warm-up: establish connection to Doubao API and pre-warm the model.
    # This cuts ~5-10s from the first user request (TCP+TLS + model cold start).
    async def _warmup():
        try:
            import httpx, os, time
            api_key = os.getenv("OPENAI_API_KEY", "")
            base_url = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
            model = os.getenv("TEXT_MODELS", "doubao-seed-2-0-mini-260428").split(",")[0].strip()
            if not api_key:
                return

            t0 = time.time()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1, "temperature": 0,
                    },
                )
            logger.info(f"API warm-up completed in {time.time()-t0:.1f}s (status={resp.status_code})")
        except Exception as e:
            logger.info(f"API warm-up skipped (non-blocking): {e}")

    import asyncio
    asyncio.create_task(_warmup())

    yield

    logger.info("Shutting down BetweenLines API...")


app = FastAPI(
    title="BetweenLines API",
    description="BetweenLines - AI-powered relationship communication companion",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS 配置 — 从环境变量读取允许的来源
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

# Security & rate limit middlewares (inner layers)
from app.middleware.security import security_headers_middleware
app.middleware("http")(security_headers_middleware)

from app.middleware.rate_limit import rate_limit_middleware
app.middleware("http")(rate_limit_middleware)

# CORS must be registered LAST so it's the OUTERMOST middleware
# (Starlette executes in reverse registration order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/")
async def root():
    import subprocess
    commit_hash = "unknown"
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            text=True,
        ).strip()
    except Exception:
        pass

    return {
        "message": "BetweenLines API is running",
        "version": "0.1.0",
        "commit": commit_hash,
    }


@app.get("/health")
async def health_check():
    import subprocess
    commit_hash = "unknown"
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            text=True,
        ).strip()
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": "0.1.0",
        "commit": commit_hash,
    }


# 注册路由
from app.routers import chat
app.include_router(chat.router)
from app.routers import review
app.include_router(review.router)
from app.routers import quality
app.include_router(quality.router)
