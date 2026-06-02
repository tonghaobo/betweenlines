"use client";

import { useRef, useEffect, useState } from "react";
import { HeroSection } from "@/components/hero/HeroSection";
import { ExampleChats } from "@/components/hero/ExampleChats";
import { ChatInput } from "@/components/chat-input/ChatInput";
import { useChatAnalysis } from "@/lib/useChatAnalysis";
import { ResultPage } from "@/components/result/ResultPage";
import { FeedbackSection } from "@/components/feedback/FeedbackSection";
import { ReplyAdoptionCard } from "@/components/feedback/ReplyAdoptionCard";
import { FollowUpReminder } from "@/components/feedback/FollowUpReminder";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { UsageLimitModal } from "@/components/ui/UsageLimitModal";
import { ShareButton } from "@/components/share/ShareButton";
import { useI18n } from "@/contexts/I18nContext";
import { track, getAnalyticsUserId } from "@/lib/analytics";
import type { RelationshipType } from "@/lib/api";

export default function Home() {
  const { t } = useI18n();
  const { result, isLoading, error, errorType, limitReached, analyze, reset } = useChatAnalysis();
  const resultRef = useRef<HTMLDivElement>(null);
  const hasTrackedPageView = useRef(false);
  const [exampleText, setExampleText] = useState("");
  const [lastRelationshipType, setLastRelationshipType] = useState<RelationshipType>("romantic");

  // Track page_view + return_visit on mount
  useEffect(() => {
    if (hasTrackedPageView.current) return;
    hasTrackedPageView.current = true;

    const id = getAnalyticsUserId();
    const isFirstVisit = !localStorage.getItem("betweenlines_returned");
    
    track("page_view", { page: "home" });

    if (!isFirstVisit) {
      track("return_visit");
    } else {
      localStorage.setItem("betweenlines_returned", "true");
    }
  }, []);

  useEffect(() => {
    if (result && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  const handleSelectExample = (text: string) => {
    reset();
    setExampleText(text);
  };

  const handleSubmit = (text: string, relationshipType: RelationshipType, source?: string) => {
    setLastRelationshipType(relationshipType);
    analyze(text, relationshipType, source);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center space-y-8">
        <HeroSection />
        <ChatInput onSubmit={handleSubmit} isLoading={true} initialText={exampleText} />
        <LoadingOverlay />
      </div>
    );
  }

  // Result page
  if (result) {
    return (
      <div className="flex flex-col items-center space-y-8">
        <button
          onClick={reset}
          className="text-sm text-blue-600 hover:text-blue-800 transition-colors self-start 
                     flex items-center gap-1 group"
        >
          <span className="group-hover:-translate-x-1 transition-transform">←</span>
          {t.errors.backToHome}
        </button>
        <div ref={resultRef}>
          <ResultPage data={result} />
        </div>
        <ShareButton data={result} relationshipType={lastRelationshipType} />
        <FeedbackSection />
        <ReplyAdoptionCard />
      </div>
    );
  }

  // Home page
  return (
    <div className="flex flex-col items-center space-y-8">
      <HeroSection />
      <ExampleChats onSelect={handleSelectExample} />
      <ChatInput onSubmit={handleSubmit} isLoading={false} initialText={exampleText} />
      <FollowUpReminder />

      {error && !limitReached && (
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
                {t.errors.tryAgain}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Usage limit modal (soft limit) */}
      <UsageLimitModal
        open={limitReached}
        onClose={reset}
      />
    </div>
  );
}
