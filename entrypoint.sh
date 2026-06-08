#!/bin/bash
set -e

# ── 颜色输出 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 检查必需的环境变量 ──
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "替换为你的豆包API_Key" ]; then
    log_error "OPENAI_API_KEY 未设置！"
    exit 1
fi

# ── 生成后端 .env（从容器环境变量） ──
log_info "生成 backend/.env 配置..."
cat > /app/backend/.env << EOF
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://ark.cn-beijing.volces.com/api/v3}
TEXT_MODELS=${TEXT_MODELS:-doubao-seed-1-8-251228}
VISION_MODELS=${VISION_MODELS:-doubao-vision-pro-32k}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000}
TEMPERATURE=${TEMPERATURE:-0.7}
MAX_TOKENS=${MAX_TOKENS:-400}
VISION_TEMPERATURE=${VISION_TEMPERATURE:-0.3}
VISION_MAX_TOKENS=${VISION_MAX_TOKENS:-2000}
MAX_CHAT_LENGTH=${MAX_CHAT_LENGTH:-2000}
MIN_CHAT_LENGTH=${MIN_CHAT_LENGTH:-10}
FREE_DAILY_LIMIT=${FREE_DAILY_LIMIT:-10}
ENABLE_SHARE_REWARD=${ENABLE_SHARE_REWARD:-true}
MAX_SHARE_REWARDS_PER_DAY=${MAX_SHARE_REWARDS_PER_DAY:-1}
EOF

# ── 端口：PORT 由 Railway 自动设置，本地默认 8000 ──
BACKEND_PORT="${PORT:-8000}"
log_info "后端监听端口: $BACKEND_PORT (PORT=${PORT:-未设置})"

# ── 启动后端 ──
log_info "启动 FastAPI 后端..."
cd /app/backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} &
BACKEND_PID=$!
log_info "后端 PID: $BACKEND_PID"

# ── 启动前端（仅本地 docker-compose，Railway 不启动） ──
FRONTEND_PID=""
if [ -z "${PORT:-}" ]; then
    # PORT 未设置 = 本地环境，启动前端
    log_info "启动 Next.js 前端 (端口 3000)..."
    cd /app/frontend
    npm start -- -H 0.0.0.0 -p 3000 &
    FRONTEND_PID=$!
    log_info "前端 PID: $FRONTEND_PID"
fi

# ── 等待服务就绪 ──
sleep 3

if kill -0 $BACKEND_PID 2>/dev/null; then
    log_info "后端运行中 → http://0.0.0.0:${BACKEND_PORT}/health"
else
    log_error "后端启动失败！"
    exit 1
fi

if [ -n "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
    log_info "前端运行中 → http://0.0.0.0:3000"
fi

echo ""
log_info "═══════════════════════════════════════"
log_info "  BetweenLines 已启动"
log_info "  后端: 0.0.0.0:${BACKEND_PORT}/health"
[ -n "$FRONTEND_PID" ] && log_info "  前端: 0.0.0.0:3000"
log_info "═══════════════════════════════════════"
echo ""

# ── 信号处理 ──
cleanup() {
    log_info "收到终止信号，正在关闭..."
    kill $BACKEND_PID 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && wait $FRONTEND_PID 2>/dev/null || true
    log_info "服务已关闭"
    exit 0
}
trap cleanup SIGTERM SIGINT

if [ -n "$FRONTEND_PID" ]; then
    wait -n $BACKEND_PID $FRONTEND_PID
else
    wait $BACKEND_PID
fi

cleanup
