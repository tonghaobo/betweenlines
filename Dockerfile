FROM ubuntu:24.04

# ── 清除 Docker daemon 注入的代理环境变量 ──
ENV HTTP_PROXY="" HTTPS_PROXY="" http_proxy="" https_proxy="" NO_PROXY="" no_proxy=""
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python 3.12 (Ubuntu 24.04 默认)
    python3 \
    python3-pip \
    python3-venv \
    # Node.js 20 LTS (via NodeSource)
    ca-certificates \
    curl \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 验证版本
RUN node -v && python3 --version

# ── 工作目录 ──
WORKDIR /app

# ── 复制项目文件 ──
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# 创建数据目录（SQLite 持久化）
RUN mkdir -p /app/backend/data

# ── 后端：创建虚拟环境 & 安装依赖 ──
RUN cd /app/backend \
    && python3 -m venv .venv \
    && . .venv/bin/activate \
    && pip install --upgrade pip --no-cache-dir \
    && pip install -r requirements.txt --no-cache-dir

# ── 前端：安装依赖 & 构建生产版本 ──
RUN cd /app/frontend \
    && npm install \
    && npm run build

# ── 启动脚本 ──
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 3000 8000

ENTRYPOINT ["/app/entrypoint.sh"]
