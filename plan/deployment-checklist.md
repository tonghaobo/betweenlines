# BetweenLines 上线 Checklist

## 前端 (Vercel)
- [ ] `vercel.json` 配置正确
- [ ] `NEXT_PUBLIC_API_URL` 环境变量已设置（指向 Railway 后端）
- [ ] `vercel --prod` 部署成功
- [ ] 自定义域名已配置（可选）
- [ ] HTTPS 正常
- [ ] 页面加载速度 < 3s
- [ ] 移动端响应式正常

## 后端 (Railway)
- [ ] `OPENAI_API_KEY` 环境变量已设置
- [ ] `OPENAI_MODEL` 设置为 `gpt-4o-mini`
- [ ] `ALLOWED_ORIGINS` 设置为前端域名
- [ ] `/health` 端点返回 200
- [ ] `/api/v1/analyze` 正常响应
- [ ] CORS 头正确
- [ ] 速率限制生效
- [ ] 错误时有友好的 JSON 响应

## 功能验证
- [ ] 粘贴聊天 → 分析 → 展示结果（端到端）
- [ ] 三种风格回复建议正常生成
- [ ] 一键复制可用
- [ ] 反馈提交可用
- [ ] 错误状态友好展示

## 安全
- [ ] API Key 未暴露在前端代码中
- [ ] 聊天记录不存储
- [ ] 速率限制生效
- [ ] 违规内容检测生效
- [ ] HTTPS 全链路

## 监控（V1 可选）
- [ ] Vercel Analytics 已启用（可选）
- [ ] Railway 日志可查看
- [ ] `/api/v1/stats` 反馈统计可访问
