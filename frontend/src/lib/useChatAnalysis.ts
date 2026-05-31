"use client";

import { useState, useCallback } from "react";
import { analyzeChat, ChatAnalysisResponse } from "./api";
import { useI18n } from "@/contexts/I18nContext";

interface UseChatAnalysisState {
  result: ChatAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  errorType: "validation" | "timeout" | "network" | "server" | "rate_limit" | null;
}

export function useChatAnalysis() {
  const { t } = useI18n();

  const [state, setState] = useState<UseChatAnalysisState>({
    result: null,
    isLoading: false,
    error: null,
    errorType: null,
  });

  const analyze = useCallback(async (chatContent: string) => {
    setState({ result: null, isLoading: true, error: null, errorType: null });
    try {
      const result = await analyzeChat(chatContent);
      setState({ result, isLoading: false, error: null, errorType: null });
    } catch (err) {
      const { message, type } = getErrorMessage(err, t.errors);
      setState({ result: null, isLoading: false, error: message, errorType: type });
    }
  }, [t.errors]);

  const reset = useCallback(() => {
    setState({ result: null, isLoading: false, error: null, errorType: null });
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
): { message: string; type: UseChatAnalysisState["errorType"] } {
  if (error instanceof Error) {
    const msg = error.message;
    if (msg.includes("timed out") || msg.includes("Timeout") || msg.includes("abort")) {
      return { message: msgs.timeout, type: "timeout" };
    }
    if (msg.includes("Network") || msg.includes("fetch") || msg.includes("Failed to fetch")) {
      return { message: msgs.network, type: "network" };
    }
    if (msg.includes("Too many requests") || msg.includes("429")) {
      return { message: msgs.rateLimit, type: "rate_limit" };
    }
    return { message: msg, type: "server" };
  }
  return { message: msgs.default, type: "server" };
}
