"use client";

import { useRef, useEffect } from "react";
import { HeroSection } from "@/components/hero/HeroSection";
import { ExampleChats } from "@/components/hero/ExampleChats";
import { ChatInput } from "@/components/chat-input/ChatInput";
import { useChatAnalysis } from "@/lib/useChatAnalysis";
import { ResultPage } from "@/components/result/ResultPage";
import { FeedbackSection } from "@/components/feedback/FeedbackSection";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";

export default function Home() {
  const { result, isLoading, error, errorType, analyze, reset } = useChatAnalysis();
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (result && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  const handleSelectExample = (text: string) => {
    reset();
  };

  // Loading 状态
  if (isLoading) {
    return (
      <div className="flex flex-col items-center space-y-8">
        <HeroSection />
        <ChatInput onSubmit={analyze} isLoading={true} />
        <LoadingOverlay />
      </div>
    );
  }

  // 结果页
  if (result) {
    return (
      <div className="flex flex-col items-center space-y-8">
        <button
          onClick={reset}
          className="text-sm text-blue-600 hover:text-blue-800 transition-colors self-start 
                     flex items-center gap-1 group"
        >
          <span className="group-hover:-translate-x-1 transition-transform">←</span>
          Analyze another chat
        </button>
        <div ref={resultRef}>
          <ResultPage data={result} />
        </div>
        <FeedbackSection />
      </div>
    );
  }

  // 首页
  return (
    <div className="flex flex-col items-center space-y-8">
      <HeroSection />
      <ExampleChats onSelect={handleSelectExample} />
      <ChatInput onSubmit={analyze} isLoading={false} />

      {error && (
        <div className="w-full max-w-lg p-4 rounded-xl text-sm animate-fade-in
                        bg-red-50 border border-red-200 text-red-700">
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0">
              {errorType === "timeout" ? "⏱️" :
               errorType === "network" ? "🌐" :
               errorType === "rate_limit" ? "🚦" : "⚠️"}
            </span>
            <div>
              <p>{error}</p>
              <button
                onClick={reset}
                className="mt-1 text-red-600 underline hover:no-underline text-xs"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
