const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REQUEST_TIMEOUT = 30000;
const MAX_RETRIES = 2;

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
    throw new ApiError(
      "Network error. Please check your connection.",
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
): Promise<ChatAnalysisResponse> {
  return retryableRequest(async () => {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/api/v1/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_content: chatContent }),
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

export async function submitFeedback(
  helpful: boolean,
  analysisId?: string,
): Promise<void> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/api/v1/feedback`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ helpful, analysis_id: analysisId || null }),
    },
    5000,
  );

  if (!response.ok) {
    console.warn("Feedback submission failed:", response.status);
  }
}
