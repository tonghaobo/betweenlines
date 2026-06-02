# Day 3-4：前端首页 UI 开发

## 任务概述
完成 BetweenLines 首页的完整 UI 开发，包括 Hero 区域、聊天输入区、交互逻辑、Loading 状态和表单验证。

**工作量：2 天**

---

## Day 3（上午）：首页组件拆分与 Hero 区域

### 任务 3.1：创建组件目录结构

在 `frontend/src/` 下创建组件目录：

```bash
cd /Users/tonghaobo/codes/chatvibe/frontend
mkdir -p src/components/hero
mkdir -p src/components/chat-input
mkdir -p src/components/ui
mkdir -p src/lib
```

### 任务 3.2：创建 Hero 组件

创建 `frontend/src/components/hero/HeroSection.tsx`：

```tsx
export function HeroSection() {
  return (
    <div className="flex flex-col items-center text-center space-y-4 py-12">
      {/* Badge */}
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-700/10">
        AI-Powered Chat Analysis
      </span>

      {/* 主标题 */}
      <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
        Understand the vibe
        <br />
        <span className="text-blue-600">before you reply.</span>
      </h1>

      {/* 副标题 */}
      <p className="text-lg text-gray-500 max-w-lg">
        Paste your chat and get instant insight on the conversation mood,
        suggested replies, and timing advice — all in seconds.
      </p>

      {/* 三个卖点 */}
      <div className="flex flex-wrap justify-center gap-6 pt-4 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          No sign-up required
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          Chat data not stored
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          Natural, not PUA
        </div>
      </div>
    </div>
  );
}
```

### 任务 3.3：创建示例占位组件

创建 `frontend/src/components/hero/ExampleChats.tsx`：

```tsx
const examples = [
  {
    label: "Casual Chat",
    content: `A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢`,
  },
  {
    label: "Short Replies",
    content: `A: 周末有什么安排吗
B: 嗯嗯
A: 最近有部电影还不错
B: 哈哈哈`,
  },
  {
    label: "Getting Cold",
    content: `A: 你平时喜欢做什么呀
B: 没什么特别的
A: 那你喜欢看电影吗
B: 还行`,
  },
];

export function ExampleChats({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <div className="flex flex-wrap justify-center gap-3 pt-2">
      <span className="text-xs text-gray-400 w-full text-center mb-1">
        Try an example:
      </span>
      {examples.map((ex) => (
        <button
          key={ex.label}
          onClick={() => onSelect(ex.content)}
          className="px-4 py-2 text-sm text-gray-600 bg-gray-50 border border-gray-200 
                     rounded-full hover:bg-gray-100 hover:border-gray-300 
                     transition-colors duration-150"
        >
          {ex.label}
        </button>
      ))}
    </div>
  );
}
```

---

## Day 3（下午）：聊天输入区组件

### 任务 3.4：创建 ChatInput 组件

创建 `frontend/src/components/chat-input/ChatInput.tsx`：

```tsx
"use client";

import { useState, useRef } from "react";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  isLoading: boolean;
  initialText?: string;
}

export function ChatInput({ onSubmit, isLoading, initialText = "" }: ChatInputProps) {
  const [text, setText] = useState(initialText);
  const [charCount, setCharCount] = useState(initialText.length);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const MAX_CHARS = 5000;
  const MIN_CHARS = 10;

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= MAX_CHARS) {
      setText(value);
      setCharCount(value.length);
    }
  };

  const handleSubmit = () => {
    if (text.trim().length >= MIN_CHARS && !isLoading) {
      onSubmit(text.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Cmd/Ctrl + Enter 提交
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isValid = text.trim().length >= MIN_CHARS;

  return (
    <div className="w-full max-w-lg space-y-3">
      {/* 输入框 */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`Paste your chat here...
Example format:
A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢`}
          className="w-full h-44 p-4 border border-gray-200 rounded-xl resize-none
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     text-gray-700 placeholder:text-gray-400 text-sm leading-relaxed
                     transition-shadow duration-200"
          disabled={isLoading}
        />
        {/* 字数统计 */}
        <div className="absolute bottom-3 right-3 text-xs text-gray-400">
          {charCount}/{MAX_CHARS}
        </div>
      </div>

      {/* 验证提示 */}
      {text.length > 0 && !isValid && (
        <p className="text-xs text-amber-600">
          Please enter at least {MIN_CHARS} characters for analysis.
        </p>
      )}

      {/* 提交按钮 */}
      <button
        onClick={handleSubmit}
        disabled={!isValid || isLoading}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <LoadingSpinner />
            Analyzing...
          </>
        ) : (
          "Analyze Chat"
        )}
      </button>

      {/* 快捷键提示 */}
      <p className="text-xs text-gray-400 text-center">
        Press <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">⌘</kbd>
        + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">Enter</kbd> to submit
      </p>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
```

### 任务 3.5：创建 API 调用工具函数

创建 `frontend/src/lib/api.ts`：

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatAnalysisResponse {
  chat_status: string;
  analysis: string;
  issues: string[];
  risks: string[];
  reply_suggestions: {
    natural: string;
    humorous: string;
    mature: string;
  };
  timing_advice: string;
}

export async function analyzeChat(chatContent: string): Promise<ChatAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ chat_content: chatContent }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function submitFeedback(helpful: boolean): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ helpful }),
  });
}
```

---

## Day 4（上午）：首页组装与状态管理

### 任务 4.1：创建自定义 Hook — useChatAnalysis

创建 `frontend/src/lib/useChatAnalysis.ts`：

```typescript
"use client";

import { useState, useCallback } from "react";
import { analyzeChat, ChatAnalysisResponse } from "./api";

interface UseChatAnalysisState {
  result: ChatAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function useChatAnalysis() {
  const [state, setState] = useState<UseChatAnalysisState>({
    result: null,
    isLoading: false,
    error: null,
  });

  const analyze = useCallback(async (chatContent: string) => {
    setState({ result: null, isLoading: true, error: null });
    try {
      const result = await analyzeChat(chatContent);
      setState({ result, isLoading: false, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setState({ result: null, isLoading: false, error: message });
    }
  }, []);

  const reset = useCallback(() => {
    setState({ result: null, isLoading: false, error: null });
  }, []);

  return {
    ...state,
    analyze,
    reset,
  };
}
```

### 任务 4.2：组装首页

重写 `frontend/src/app/page.tsx`：

```tsx
"use client";

import { HeroSection } from "@/components/hero/HeroSection";
import { ExampleChats } from "@/components/hero/ExampleChats";
import { ChatInput } from "@/components/chat-input/ChatInput";
import { useChatAnalysis } from "@/lib/useChatAnalysis";
import { ResultPage } from "@/components/result/ResultPage";
import { FeedbackSection } from "@/components/feedback/FeedbackSection";

export default function Home() {
  const { result, isLoading, error, analyze, reset } = useChatAnalysis();

  const handleSelectExample = (text: string) => {
    // 示例文本选择后，由于 ChatInput 是受控组件，
    // 我们需要通过一个 ref 或者提升状态来实现
    // 此处简化：先重置，用户点击示例后自动填入
    reset();
  };

  // 如果已有分析结果，显示结果页
  if (result) {
    return (
      <div className="flex flex-col items-center space-y-8">
        <button
          onClick={reset}
          className="text-sm text-blue-600 hover:text-blue-800 transition-colors self-start"
        >
          ← Analyze another chat
        </button>
        <ResultPage data={result} />
        <FeedbackSection />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-8">
      <HeroSection />
      <ExampleChats onSelect={handleSelectExample} />
      <ChatInput onSubmit={analyze} isLoading={isLoading} />

      {/* 错误提示 */}
      {error && (
        <div className="w-full max-w-lg p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
          <button
            onClick={reset}
            className="ml-2 underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
```

**注意：** `ResultPage` 和 `FeedbackSection` 组件将在 Day 4 下午和 Day 9-10 分别完成。Day 4 可以先创建占位文件。

### 任务 4.3：创建占位组件（结果页和反馈）

创建 `frontend/src/components/result/ResultPage.tsx`（占位）：

```tsx
import { ChatAnalysisResponse } from "@/lib/api";

interface ResultPageProps {
  data: ChatAnalysisResponse;
}

export function ResultPage({ data }: ResultPageProps) {
  return (
    <div className="w-full max-w-2xl space-y-6">
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Chat Status: {data.chat_status}
        </h2>
        <p className="text-gray-600">{data.analysis}</p>
      </div>
      {/* TODO: Day 7-8 完善结果展示 */}
    </div>
  );
}
```

创建 `frontend/src/components/feedback/FeedbackSection.tsx`（占位）：

```tsx
export function FeedbackSection() {
  return (
    <div className="w-full max-w-2xl card text-center">
      <p className="text-gray-600 mb-3">这个建议有帮助吗？</p>
      <div className="flex justify-center gap-4">
        <button className="px-6 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors">
          👍 有帮助
        </button>
        <button className="px-6 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors">
          👎 没帮助
        </button>
      </div>
    </div>
  );
}
```

---

## Day 4（下午）：UI 细节与响应式适配

### 任务 4.4：响应式优化

检查并确保以下元素在各尺寸下表现良好：

- **移动端（< 640px）**：输入框全宽，Hero 标题缩小至 `text-3xl`，按钮全宽
- **平板端（640px - 1024px）**：居中布局，max-w-lg
- **桌面端（> 1024px）**：居中布局，max-w-2xl，更大字体

在 `frontend/tailwind.config.ts` 中确认响应式断点配置（Next.js 默认已配置）。

### 任务 4.5：动画细节

在 `frontend/tailwind.config.ts` 中添加动画配置：

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      animation: {
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.5s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

### 任务 4.6：Meta 信息与 SEO

编辑 `frontend/src/app/layout.tsx`，确保 meta 信息完整（已在 Day 1 设置，确认即可）。

创建 `frontend/src/app/robots.ts`：

```typescript
import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
  };
}
```

创建 `frontend/src/app/sitemap.ts`：

```typescript
import { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://betweenlines.tech",
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
```

---

## 验收标准（Day 4 结束）

- [ ] 首页完整渲染：Hero + 示例选择 + 输入框 + 分析按钮
- [ ] 输入框字数统计正常（10~5000 字符限制）
- [ ] 示例点击可填入输入框（需完善交互）
- [ ] Loading 状态：按钮显示 "Analyzing..." 并带旋转动画
- [ ] 错误状态：显示错误提示和重试链接
- [ ] Cmd+Enter 快捷键可触发提交
- [ ] 移动端适配正常（375px 宽度下 UI 不错乱）
- [ ] Tailwind 动画配置生效
- [ ] 结果页占位组件可正常显示

## 给 AI 的执行提示

```
请按照以上步骤，依次完成 Day 3 和 Day 4 的所有任务。
先创建组件目录和文件，再编写组件代码，最后组装到首页。
每个组件创建后，可以通过 npm run dev 在浏览器中验证渲染效果。
ResultPage 和 FeedbackSection 先做占位即可，详细实现留到 Day 7-8。
注意 useChatAnalysis hook 需要在 page.tsx 标记为 "use client"。
如果遇到 TypeScript 类型错误，请确认 api.ts 中的类型定义正确。
```
