# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## Commands

```bash
# Backend — start dev (port 8000)
cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --reload --port 8000

# Backend — commit gate validation (no AI, <5s)
python tests/test_comprehensive.py --no-ai

# Backend — full tests (requires AI)
python tests/test_comprehensive.py

# Frontend — start dev (port 3000)
cd frontend && npm run dev

# Frontend — build check (commit gate)
npx next build --no-lint 2>&1 | tail -5
```

**Setup**: Backend needs `backend/.env` (OPENAI_API_KEY, OPENAI_BASE_URL, ALLOWED_ORIGINS). Frontend needs `frontend/.env.local` (NEXT_PUBLIC_API_URL=http://localhost:8000). `docker compose up -d` for all-in-one.

## Architecture

**BetweenLines** — AI chat analysis tool. Users paste chat logs → AI analyzes tone, detects turning points, predicts reply trajectory, gives 3 reply styles. Not a chatbot.

**Tech stack**: Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 (frontend) / FastAPI + Python 3.11 + Pydantic v2 (backend) / Doubao API via 火山引擎 ARK (OpenAI-compatible) / SQLite (storage).

**Flow**: `Browser → Next.js :3000 → FastAPI :8000 → Doubao API → SQLite`. Dev mode proxies API through Next.js `rewrites`; production calls backend directly.

### Backend

- **`main.py`**: Registers CORS (outermost), rate limit, security headers as middleware. Starlette runs in reverse registration order — CORS must be last `add_middleware` call.
- **`routers/chat.py`** (`/api/v1`): 10 endpoints — analyze, analyze-screenshot, feedback, outcome, stats, usage, track, share-reward, metrics.
- **`routers/review.py`** (`/api/v1`): 1 endpoint — review (post-reply follow-up comparison).
- **`services/doubao_service.py`**: Core AI service. `analyze_chat()` pipeline: pre-extract statistical features (emoji count, emotion words, short-reply ratio via CPU-only regex) → build System Prompt with 8 analysis dimensions → inject static few-shot + dynamic examples from `good_cases` table → call Doubao with multi-model fallback on quota errors → parse JSON → posterior quality check. `extract_text_from_screenshot()` calls vision model for OCR.
- **Input pipeline order** (in `/analyze`): cache check (SHA-256, 10min TTL) → quota check → validation (10-5000 chars, harmful keywords) → clean + normalize (auto-parse WeChat format) → AI analysis → cache result → log.
- **Few-shot learning without storing chat**: 👍 triggers saving only statistical features + AI analysis JSON to `good_cases`. Raw chat text never touches disk.
- **Multi-model fallback**: TEXT_MODELS env var is comma-separated list. Service iterates on HTTP 429/403/503.
- **DB tables**: `feedback`, `outcome`, `analysis_log`, `good_cases` (features only, no raw text), `feedback_rewards`, `share_rewards`, `events`.

### Frontend

- **Single-page app** at `/` (`page.tsx` client component owns all state). Three views: landing → loading overlay → result cards. `/admin/metrics` is the only other page.
- **`useChatAnalysis` hook** (`lib/useChatAnalysis.ts`): State management for analysis flow. Results + OCR text persist to `sessionStorage` (30min TTL) for refresh survivability.
- **`lib/api.ts`**: Native fetch + AbortController. 30s timeout for analyze, 300s for OCR. Exponential backoff retry (max 2). Typed `ApiError` with categorized error UI.
- **V2 Landing Page**: `HeroSection → DemoAnalysis → InputBox → FeaturesSection → SocialProof`. Result view: `ResultPage` (StatusBadge + AnalysisCard + ReplySuggestions ×3 + TimingAdvice) → `FeedbackSection` + `ReplyAdoptionCard`.
- **i18n**: React Context, SSR-safe (first render `en`, client `useEffect` restores). `zh.ts` uses `satisfies typeof en` for key parity.
- **InputBox (V2)**: Unified text/image entry — auto-detects type, OCR intercepts images for user confirmation, supports multi-batch screenshot append.

### Critical Constraints

- ❌ No absolute judgments ("she likes you"), no auto-sending messages, no PUA/anxiety tactics
- ❌ Chat content never stored to disk (memory-only during request)
- ❌ No Redux/Zustand, no CSS-in-JS, no Axios
- ❌ Functions ≤100 lines, no speculative features
