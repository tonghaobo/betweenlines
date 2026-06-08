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
    echo ""
    echo "请在 docker-compose.yml 中设置你的豆包 API Key："
    echo "  environment:"
    echo "    - OPENAI_API_KEY=ark-xxxxxxxxxx"
    echo ""
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

# ── 生成前端 .env.local ──
log_info "生成 frontend/.env.local 配置..."
BACKEND_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
cat > /app/frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=${BACKEND_URL}
EOF

# ── 启动后端 ──
log_info "启动 FastAPI 后端 (端口 8000)..."
cd /app/backend
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
log_info "后端 PID: $BACKEND_PID"

# ── 启动前端 (生产模式) ──
log_info "启动 Next.js 前端 (端口 3000)..."
cd /app/frontend
npm start -- -H 0.0.0.0 -p 3000 &
FRONTEND_PID=$!
log_info "前端 PID: $FRONTEND_PID"

# ── 等待健康检查 ──
log_info "等待服务就绪..."
sleep 3

# 验证后端
if kill -0 $BACKEND_PID 2>/dev/null; then
    log_info "后端运行中 → http://localhost:8000/health"
else
    log_error "后端启动失败！"
fi

# 验证前端
if kill -0 $FRONTEND_PID 2>/dev/null; then
    log_info "前端运行中 → http://localhost:3000"
else
    log_error "前端启动失败！"
fi

echo ""
log_info "═══════════════════════════════════════"
log_info "  BetweenLines 已启动"
log_info "  前端: http://localhost:3000"
log_info "  后端: http://localhost:8000/health"
log_info "═══════════════════════════════════════"
echo ""

# ── 信号处理：优雅关闭 ──
cleanup() {
    log_info "收到终止信号，正在关闭服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    wait $FRONTEND_PID 2>/dev/null || true
    log_info "服务已关闭。"
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── 等待任一子进程退出 ──
wait -n $BACKEND_PID $FRONTEND_PID
EXIT_CODE=$?
log_warn "一个服务进程退出 (code=$EXIT_CODE)，关闭所有服务..."
cleanup
