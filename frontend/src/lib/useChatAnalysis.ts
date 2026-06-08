"use client";

import { useState, useCallback } from "react";
import { analyzeChat, ChatAnalysisResponse, type RelationshipType } from "./api";
import { track, getAnalyticsUserId } from "./analytics";
import { useI18n } from "@/contexts/I18nContext";

interface UseChatAnalysisState {
  result: ChatAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  errorType: "validation" | "timeout" | "network" | "server" | "rate_limit" | "daily_limit" | null;
  limitReached: boolean;
}

export function useChatAnalysis() {
  const { t } = useI18n();

  const [state, setState] = useState<UseChatAnalysisState>({
    result: null,
    isLoading: false,
    error: null,
    errorType: null,
    limitReached: false,
  });

  const analyze = useCallback(async (chatContent: string, relationshipType: RelationshipType = "romantic", source?: string, language?: string) => {
    setState({ result: null, isLoading: true, error: null, errorType: null, limitReached: false });

    // Track analysis_created
    track("analysis_created", { chat_length: chatContent.length, relationship_type: relationshipType, source: source ?? "text" });

    const startTime = Date.now();

    try {
      const anonymousUserId = getAnalyticsUserId();
      const result = await analyzeChat(chatContent, relationshipType, anonymousUserId, source, language);
      
      // Track analysis_success + reply_generated
      const durationMs = Date.now() - startTime;
      track("analysis_success", { duration_ms: durationMs, relationship_type: relationshipType });
      track("reply_generated");

      setState({ result, isLoading: false, error: null, errorType: null, limitReached: false });
    } catch (err) {
      const { message, type, isDailyLimit } = getErrorMessage(err, t.errors);
      if (isDailyLimit) {
        track("usage_limit_hit", { type: "analysis" });
      }
      setState({ result: null, isLoading: false, error: message, errorType: type, limitReached: isDailyLimit });
    }
  }, [t.errors]);

  const reset = useCallback(() => {
    setState({ result: null, isLoading: false, error: null, errorType: null, limitReached: false });
  }, []);

  return {
    ...state,
    analyze,
    reset,
  };
}

function getErrorMessage(
  error: unknown,
  msgs: typeof import("@/locales/en").default.errors,
): { message: string; type: UseChatAnalysisState["errorType"]; isDailyLimit: boolean } {
  if (error instanceof Error) {
    const msg = error.message;
    if (msg.includes("timed out") || msg.includes("Timeout") || msg.includes("abort")) {
      return { message: msgs.timeout, type: "timeout", isDailyLimit: false };
    }
    if (msg.includes("Network") || msg.includes("fetch") || msg.includes("Failed to fetch")) {
      return { message: msgs.network, type: "network", isDailyLimit: false };
    }
    if (msg.includes("Too many requests") || (msg.includes("429") && !msg.includes("daily_limit_reached"))) {
      return { message: msgs.rateLimit, type: "rate_limit", isDailyLimit: false };
    }
    // Daily limit: backend returns "daily_limit_reached" as detail
    if (msg.includes("daily_limit_reached") || msg.includes("上限") || msg.includes("limit reached") || msg.includes("Daily") || msg.includes("已达") || msg.includes("已用完")) {
      return { message: msgs.dailyLimit, type: "daily_limit", isDailyLimit: true };
    }
    return { message: msg, type: "server", isDailyLimit: false };
  }
  return { message: msgs.default, type: "server", isDailyLimit: false };
}
