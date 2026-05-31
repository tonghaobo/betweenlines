"use client";

import { useState, useCallback } from "react";
import { analyzeChat, ChatAnalysisResponse } from "./api";

interface UseChatAnalysisState {
  result: ChatAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  errorType: "validation" | "timeout" | "network" | "server" | "rate_limit" | null;
}

function getErrorMessage(error: unknown): { message: string; type: UseChatAnalysisState["errorType"] } {
  if (error instanceof Error) {
    const msg = error.message;
    if (msg.includes("timed out") || msg.includes("Timeout") || msg.includes("abort")) {
      return { message: "请求超时，请检查网络后重试。", type: "timeout" };
    }
    if (msg.includes("Network") || msg.includes("fetch") || msg.includes("Failed to fetch")) {
      return { message: "网络连接失败，请检查网络设置。", type: "network" };
    }
    if (msg.includes("Too many requests") || msg.includes("429")) {
      return { message: "请求过于频繁，请稍后再试。", type: "rate_limit" };
    }
    return { message: msg, type: "server" };
  }
  return { message: "Something went wrong.", type: "server" };
}

export function useChatAnalysis() {
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
      const { message, type } = getErrorMessage(err);
      setState({ result: null, isLoading: false, error: message, errorType: type });
    }
  }, []);

  const reset = useCallback(() => {
    setState({ result: null, isLoading: false, error: null, errorType: null });
  }, []);

  return {
    ...state,
    analyze,
    reset,
  };
}
