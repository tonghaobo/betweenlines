"use client";

import { Suspense, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useI18n } from "@/contexts/I18nContext";
import { reviewChat, type ReviewResponse } from "@/lib/api";
import { ReviewSummaryCard } from "@/components/review/ReviewSummaryCard";
import { ConversationDiff } from "@/components/review/ConversationDiff";
import { NextStepAdvice } from "@/components/review/NextStepAdvice";

function ReviewPageContent() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const analysisIdParam = searchParams.get("analysis_id");

  const [chatContent, setChatContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ReviewResponse | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!chatContent.trim() || !analysisIdParam) return;
    const analysisId = parseInt(analysisIdParam, 10);
    if (isNaN(analysisId)) {
      setError("无法找到上次分析记录。");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const res = await reviewChat(analysisId, chatContent, "romantic");
      setResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "复盘分析失败，请稍后重试。";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [chatContent, analysisIdParam]);

  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto max-w-2xl px-4 py-12 space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-gray-900">
            {t.review?.title || "回复后复盘"}
          </h1>
          <p className="text-sm text-gray-500">
            {t.review?.subtitle || "把后续聊天贴回来，看看上次建议有没有效"}
          </p>
        </div>

        {/* Result view */}
        {result ? (
          <div className="space-y-6 animate-fade-in">
            <ReviewSummaryCard data={result} />
            <ConversationDiff changes={result.changes} />
            <NextStepAdvice
              effectiveness={result.previous_advice_effectiveness}
              advice={result.next_step_advice}
            />
            <div className="flex justify-center gap-3 pt-4">
              <button
                onClick={() => router.push("/")}
                className="px-4 py-2 text-sm text-blue-600 hover:text-blue-700 border border-blue-200 rounded-xl transition-colors"
              >
                ← {t.errors?.backToHome || "返回首页"}
              </button>
            </div>
          </div>
        ) : (
          /* Input view */
          <div className="space-y-4">
            <textarea
              className="w-full h-48 rounded-2xl border border-gray-200 p-4 text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300
                         resize-none transition-all"
              placeholder={t.review?.inputPlaceholder || "粘贴后续聊天记录...\n\n例如：\n她：哈哈好呀，下周吧～\n我：行，那下周联系你"}
              value={chatContent}
              onChange={(e) => setChatContent(e.target.value)}
              disabled={isLoading}
            />

            {!analysisIdParam && (
              <p className="text-sm text-amber-600 bg-amber-50 rounded-xl px-4 py-3 border border-amber-100">
                {t.review?.noAnalysisId || "无法找到上次分析记录，请从分析结果页进入复盘。"}
              </p>
            )}

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3 border border-red-100">
                {error}
              </p>
            )}

            <button
              onClick={handleSubmit}
              disabled={isLoading || !chatContent.trim() || !analysisIdParam}
              className="w-full py-3 rounded-xl font-medium text-sm text-white
                         bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed
                         transition-all"
            >
              {isLoading
                ? (t.review?.analyzing || "复盘分析中...")
                : (t.review?.submitBtn || "开始复盘分析")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-pulse text-gray-400 text-sm">Loading...</div>
      </div>
    }>
      <ReviewPageContent />
    </Suspense>
  );
}
