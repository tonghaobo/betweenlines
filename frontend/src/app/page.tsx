"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { HeroSection } from "@/components/hero/HeroSection";
import { DemoAnalysis } from "@/components/home/DemoAnalysis";
import { FeaturesSection } from "@/components/home/FeaturesSection";
import { SocialProof } from "@/components/home/SocialProof";
import { InputBox } from "@/components/chat-input/InputBox";
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

const DEMO_CHAT_TEXT =
  "她：哈哈哈哈\n我：周末一起吃饭吗\n她：最近有点忙～";

export default function Home() {
  const { t, locale } = useI18n();
  const { result, isLoading, error, errorType, limitReached, analyze, reset } = useChatAnalysis();
  const resultRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLDivElement>(null);
  const hasTrackedPageView = useRef(false);
  const [exampleText, setExampleText] = useState("");
  const [relationshipType, setRelationshipType] = useState<RelationshipType>("romantic");
  const [lastRelationshipType, setLastRelationshipType] = useState<RelationshipType>("romantic");
  const hasTrackedFirstAnalysis = useRef(false);

  // Track page_view + return_visit on mount
  useEffect(() => {
    if (hasTrackedPageView.current) return;
    hasTrackedPageView.current = true;

    const isFirstVisit = !localStorage.getItem("betweenlines_returned");

    track("page_view", { page: "home" });

    if (!isFirstVisit) {
      track("return_visit");
    } else {
      localStorage.setItem("betweenlines_returned", "true");
    }

    // Bounce tracking: if user leaves within 10s
    const mountTime = Date.now();
    const bounceTimer = setTimeout(() => {
      // User stayed >10s, cancel bounce tracking
    }, 10000);

    const handleBeforeUnload = () => {
      if (Date.now() - mountTime < 10000) {
        // Use sendBeacon for reliable before-unload delivery
        const uid = getAnalyticsUserId();
        const body = JSON.stringify({
          anonymous_user_id: uid,
          event_name: "bounce_under_10s",
          properties: null,
          session_id: sessionStorage.getItem("betweenlines_session_id") || "sess_unknown",
        });
        try {
          navigator.sendBeacon(
            `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/track`,
            body,
          );
        } catch { /* silent */ }
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      clearTimeout(bounceTimer);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  useEffect(() => {
    if (result && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  // Track first_analysis_success when result arrives
  const hasTrackedFirstSuccess = useRef(false);
  useEffect(() => {
    if (result && hasTrackedFirstAnalysis.current && !hasTrackedFirstSuccess.current) {
      hasTrackedFirstSuccess.current = true;
      track("first_analysis_success");
    }
  }, [result]);

  const handleSubmit = useCallback((text: string, relType: RelationshipType, source?: string) => {
    setRelationshipType(relType);
    setLastRelationshipType(relType);

    // Track first analysis
    if (!hasTrackedFirstAnalysis.current) {
      hasTrackedFirstAnalysis.current = true;
      track("first_analysis_started");
    }

    const cleaned = text.replace(/\n---\n/g, "\n").replace(/^---\n/g, "").replace(/\n---$/g, "");
    analyze(cleaned, relType, source, locale);
  }, [analyze, locale]);

  // Scroll handlers for CTAs
  const scrollToInput = () => {
    inputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    // Focus textarea after scroll
    setTimeout(() => {
      const textarea = inputRef.current?.querySelector("textarea");
      textarea?.focus();
    }, 500);
  };

  const scrollToDemo = () => {
    const el = document.getElementById("demo-analysis");
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Demo fill → auto analyze
  const handleDemoFill = useCallback((text: string) => {
    setExampleText(text);
    // Small delay to let text populate, then auto-analyze
    setTimeout(() => {
      handleSubmit(text, relationshipType, "demo");
    }, 100);
  }, [relationshipType, handleSubmit]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center space-y-8">
        <HeroSection onTryFree={scrollToInput} onSeeExample={scrollToDemo} />
        <div ref={inputRef}>
          <InputBox
            onSubmit={handleSubmit}
            isLoading={true}
            initialText={exampleText}
            relationshipType={relationshipType}
            onRelationshipChange={setRelationshipType}
          />
        </div>
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

  // Home page — V2 structure
  return (
    <div className="flex flex-col items-center space-y-4">
      {/* 1. Hero — strong value prop */}
      <HeroSection onTryFree={scrollToInput} onSeeExample={scrollToDemo} />

      {/* 2. Demo Analysis — show product value immediately */}
      <DemoAnalysis onTryMyChat={scrollToInput} />

      {/* 3. Input — start experience */}
      <div ref={inputRef}>
        <InputBox
          onSubmit={handleSubmit}
          isLoading={false}
          initialText={exampleText}
          relationshipType={relationshipType}
          onRelationshipChange={setRelationshipType}
          demoChatText={DEMO_CHAT_TEXT}
          onDemoFill={handleDemoFill}
        />
      </div>

      {/* 4. Features — user benefits */}
      <FeaturesSection />

      {/* 5. Social Proof — early tester feedback */}
      <SocialProof />

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
