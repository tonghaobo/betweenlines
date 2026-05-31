import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Chat Coach API...")
    try:
        from app.services.storage import init_db
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init skipped: {e}")
    
    yield
    
    logger.info("Shutting down Chat Coach API...")


app = FastAPI(
    title="Chat Coach API",
    description="Chat Coach - AI-powered chat analysis and reply suggestions",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置 — 从环境变量读取允许的来源
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Security headers middleware
from app.middleware.security import security_headers_middleware
app.middleware("http")(security_headers_middleware)

# Rate limit middleware
from app.middleware.rate_limit import rate_limit_middleware
app.middleware("http")(rate_limit_middleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/")
async def root():
    import platform
    return {
        "message": "Chat Coach API is running",
        "version": "0.1.0",
        "python": platform.python_version(),
    }


@app.get("/health")
async def health_check():
    import platform
    return {
        "status": "healthy",
        "version": "0.1.0",
        "python": platform.python_version(),
    }


# 注册路由
from app.routers import chat
app.include_router(chat.router)
