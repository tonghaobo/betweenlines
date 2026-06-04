const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REQUEST_TIMEOUT = 30000;
const SCREENSHOT_TIMEOUT = 300000; // 截图分析最多等待5分钟（视觉模型可能较慢）
const MAX_RETRIES = 2;

export type RelationshipType = "romantic" | "friend" | "family" | "coworker" | "other";

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

export interface ScreenshotAnalysisResponse {
  extracted_text: string;
  image_preview?: string;
}

export interface UsageInfo {
  analysis_used: number;
  analysis_limit: number;
  analysis_reward: number;
  screenshot_used: number;
  screenshot_limit: number;
  max_chat_length: number;
  max_screenshots_per_request: number;
  share_reward_enabled: boolean;
}

export interface ShareRewardResponse {
  granted: boolean;
  bonus_count: number;
  message: string;
}

class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public isTimeout: boolean = false,
    public isNetworkError: boolean = false,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError("Request timed out. Please try again.", 408, true);
    }
    // Preserve original error message for better debugging
    const message = error instanceof Error ? error.message : "Network error. Please check your connection.";
    throw new ApiError(
      message,
      0,
      false,
      true,
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

async function retryableRequest<T>(
  fn: () => Promise<T>,
  maxRetries: number = MAX_RETRIES,
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (error instanceof ApiError && error.statusCode === 400) {
        throw error;
      }
      if (error instanceof ApiError && error.statusCode === 429) {
        throw error;
      }

      if (attempt === maxRetries) {
        throw lastError;
      }

      const delay = Math.pow(2, attempt) * 1000;
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

export async function analyzeChat(
  chatContent: string,
  relationshipType: RelationshipType = "romantic",
  anonymousUserId: string,
  source?: string,
): Promise<ChatAnalysisResponse> {
  return retryableRequest(async () => {
    const body: Record<string, unknown> = {
      chat_content: chatContent,
      relationship_type: relationshipType,
      anonymous_user_id: anonymousUserId,
    };
    if (source) body.source = source;

    const response = await fetchWithTimeout(
      `${API_BASE_URL}/api/v1/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      },
      REQUEST_TIMEOUT,
    );

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const detail =
        errorBody.detail || `Request failed with status ${response.status}`;
      throw new ApiError(detail, response.status);
    }

    const data = await response.json();

    if (!data.chat_status || !data.reply_suggestions) {
      throw new ApiError(
        "Invalid response format from server.",
        response.status,
      );
    }

    return data as ChatAnalysisResponse;
  });
}

export async function analyzeScreenshot(
  files: File[],
  anonymousUserId: string,
): Promise<ScreenshotAnalysisResponse> {
  return retryableRequest(async () => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    // Append anonymous_user_id as query param
    const params = new URLSearchParams({ anonymous_user_id: anonymousUserId });

    const response = await fetchWithTimeout(
      `${API_BASE_URL}/api/v1/analyze-screenshot?${params.toString()}`,
      {
        method: "POST",
        body: formData,
      },
      SCREENSHOT_TIMEOUT,
    );

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const detail =
        errorBody.detail || `Upload failed with status ${response.status}`;
      throw new ApiError(detail, response.status);
    }

    const data = await response.json();
    if (!data.extracted_text) {
      throw new ApiError("No text extracted from screenshot.", response.status);
    }

    return data as ScreenshotAnalysisResponse;
  });
}

export async function submitFeedback(
  helpful: boolean,
  analysisId?: string,
  reason: string[] = [],
  comment: string = "",
): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/api/v1/feedback`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        helpful,
        analysis_id: analysisId || null,
        reason,
        comment,
      }),
    },
    5000,
  );

  if (!response.ok) {
    console.warn("Feedback submission failed:", response.status);
  }
}

export async function submitOutcome(
  replyUsed: string,
  outcome: string = "",
  analysisId?: string,
): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/api/v1/outcome`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        analysis_id: analysisId || null,
        reply_used: replyUsed,
        outcome,
      }),
    },
    5000,
  );

  if (!response.ok) {
    console.warn("Outcome submission failed:", response.status);
  }
}

export async function getUsage(anonymousUserId: string): Promise<UsageInfo> {
  const params = new URLSearchParams({ anonymous_user_id: anonymousUserId });
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/api/v1/usage?${params.toString()}`,
    { method: "GET" },
    5000,
  );

  if (!response.ok) {
    console.warn("Usage fetch failed:", response.status);
    return { analysis_used: 0, analysis_limit: 3, analysis_reward: 0, screenshot_used: 0, screenshot_limit: 1, max_chat_length: 2000, max_screenshots_per_request: 3, share_reward_enabled: false };
  }

  return response.json();
}

export async function claimShareReward(
  anonymousUserId: string,
  shareType: string,
  shareHash: string,
): Promise<ShareRewardResponse> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/api/v1/share-reward`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        anonymous_user_id: anonymousUserId,
        share_type: shareType,
        share_hash: shareHash,
      }),
    },
    5000,
  );

  if (!response.ok) {
    return { granted: false, bonus_count: 0, message: "Reward claim failed" };
  }

  return response.json();
}
