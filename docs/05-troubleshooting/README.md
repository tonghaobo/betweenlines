# 问题排查

## 已知问题与解决方案

### 1. 通过局域网 IP 访问时中英文切换按钮无反应

**现象**：`http://localhost:3000` 正常，`http://192.168.31.195:3000` 点击按钮没反应。

**根因**：Next.js 开发模式（`next dev`）的 Webpack HMR WebSocket 在通过 IP 访问时握手失败（`ERR_INVALID_HTTP_RESPONSE`），反复重试的错误阻塞了 React 事件系统。

**解决方案**：使用生产模式启动
```bash
cd frontend
npm run build && npm start -- -H 0.0.0.0 -p 3000
```

**注意**：日常开发仍用 `npm run dev` 通过 `localhost` 访问。`dev` 命令已配置 `-H 0.0.0.0` 绑定所有接口。

---

### 2. 前端修改环境变量不生效

**现象**：修改 `.env.local` 后前端仍然使用旧值。

**原因**：Next.js 的 `NEXT_PUBLIC_*` 变量在构建时注入。

**解决方案**：重启 `npm run dev` 或重新 `npm run build`。

---

### 3. 后端 CORS 错误

**现象**：浏览器 Console 出现 `Access-Control-Allow-Origin` 相关错误。

**原因**：`ALLOWED_ORIGINS` 不包含当前前端地址。

**解决方案**：
1. 检查 `backend/.env` 中 `ALLOWED_ORIGINS` 是否包含前端地址
2. 多个地址用逗号分隔，如：`http://localhost:3000,http://192.168.31.195:3000`
3. 开发模式下，Next.js 的 rewrite 代理可以绕过 CORS（访问同源 `/api/` 路径）

---

### 4. `pip install` 报 `externally-managed-environment`

**现象**：执行 `pip install` 时报错。

**原因**：没有激活虚拟环境。

**解决方案**：
```bash
cd backend
source .venv/bin/activate  # 确认提示符前出现 (.venv)
pip install -r requirements.txt
```

---

### 5. 截图分析报错"分析失败"

**现象**：上传截图后分析失败。

**排查步骤**：
1. 确认 `backend/.env` 中 `OPENAI_API_KEY` 正确（应是以 `ark-` 开头的豆包 Key）
2. 确认系统环境变量没有覆盖 `.env`（项目使用 `override=True` 加载 `.env`）
3. 验证方式：
```bash
cd backend
source .venv/bin/activate
python -c "from app.core.config import settings; print(settings.OPENAI_API_KEY[:20])"
# 应输出 ark- 开头
```

---

### 6. 首次启动后端报 `ModuleNotFoundError`

**现象**：`ModuleNotFoundError: No module named 'xxxx'`

**原因**：依赖未安装或虚拟环境未激活。

**解决方案**：
1. 确认终端提示符前有 `(.venv)`
2. 执行 `pip install -r requirements.txt`

---

### 7. 前后端通讯不通

**排查步骤**：
1. 确认后端启动：`curl http://localhost:8000/health` 返回 `{"status":"healthy"}`
2. 确认前端 API 配置：`NEXT_PUBLIC_API_URL` 指向正确的后端地址
3. 开发模式下，Next.js rewrite 将 `/api/` 代理到 `localhost:8000`
4. 检查后端 `ALLOWED_ORIGINS` CORS 配置

---

### 8. 后端日志出现 `OPTIONS /api/v1/track 400 Bad Request`

**现象**：后端频繁收到 OPTIONS 预检请求并返回 400。

**根因**：`analytics.ts` 的 `API_BASE_URL` 默认值为 `http://localhost:8000`，绕过 Next.js rewrite 直连后端，触发浏览器 CORS 预检。

**解决方案**：已修复 — `analytics.ts` 的 `API_BASE_URL` 改为空字符串（和 `api.ts` 一致），开发模式走 rewrite 同源代理。另外 `main.py` 的 CORS 中间件调整到最外层注册顺序。

---

### 9. Railway 部署后 502 Bad Gateway

**现象**：Railway 容器正常启动，但访问返回 502。

**根因**：Railway 通过 `PORT` 环境变量指定路由端口，但 `entrypoint.sh` 硬编码了 8000/3000，未读取 `PORT`。

**解决方案**：`entrypoint.sh` 已修复 — 后端监听 `${PORT:-8000}`，Railway 上只启动后端（前端在 Vercel）。需在 Railway 清除构建缓存后重新部署。

---

### 10. 刷新页面出现 Hydration Mismatch 报错

**现象**：刷新结果页时 React 报错 `Hydration failed because the initial UI does not match`。

**根因**：`useChatAnalysis` 在 `useState` 初始化器中从 `sessionStorage` 读取缓存的分析结果。SSR 时 `result=null` → 渲染首页 `space-y-4`，客户端水合时 `result=缓存数据` → 渲染结果页 `space-y-8` + 返回按钮。

**解决方案**：将 `sessionStorage` 读取从 `useState` 初始化器移至 `useEffect`（仅在客户端挂载后执行）。

---

### 11. 并发请求触发限流后返回 500 而非 429

**现象**：短时间内大量请求时返回 `500 Internal Server Error` 而非正确的 `429 Too Many Requests`。

**根因**：限流中间件使用 `HTTPException` 抛异常，但 Starlette `BaseHTTPMiddleware` 不会正确传播 `HTTPException`。

**解决方案**：改为直接返回 `JSONResponse(status_code=429, ...)`。

---

### 12. 分析耗时过长（>30s）

**现象**：上传聊天记录后分析耗时超过 30 秒。

**根因**：（1）Prompt 增强后 Few-Shot 示例过长导致 AI 输出膨胀；（2）默认超时设置偏低。

**解决方案**：精简 Few-Shot 示例、系统 Prompt 限制输出长度（200 字）、调高超时（httpx 60s, SDK 45s, 前端 50s）。预期耗时 8-20s。

---

### 13. 前端 Next.js dev server CPU 100% 卡死

**现象**：长时间运行后 `next-server` 进程 CPU 占用飙升到 140%+，页面无法访问。

**根因**：Turbopack 开发服务器内存泄漏（长时间运行后）。

**解决方案**：`kill` 旧进程后重启 `next dev` 即可恢复。
