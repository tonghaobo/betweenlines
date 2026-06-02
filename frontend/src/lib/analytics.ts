/**
 * Analytics SDK for BetweenLines V1
 * 
 * - Auto-generates and persists anonymous_user_id (bl_xxxxx)
 * - Auto-generates session_id per browser session
 * - Provides track() for event logging
 * - Silent failures — never blocks user experience
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ANONYMOUS_ID_KEY = "betweenlines_anonymous_id";
const SESSION_ID_KEY = "betweenlines_session_id";

/**
 * Fallback: read/write cookie for anonymous user ID.
 * Used when localStorage is unavailable (privacy mode, storage full, etc).
 */
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function setCookie(name: string, value: string, maxAgeSeconds: number = 365 * 86400): void {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)};path=/;max-age=${maxAgeSeconds};SameSite=Lax`;
}

// Dedup guard: prevent identical events within 1s
const recentEvents = new Map<string, number>();
const DEDUP_WINDOW_MS = 1000;

function generateId(prefix: string): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let id = "";
  for (let i = 0; i < 8; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return `${prefix}_${id}`;
}

function getAnonymousUserId(): string {
  if (typeof window === "undefined") return "bl_ssr";

  try {
    const existing = localStorage.getItem(ANONYMOUS_ID_KEY);
    if (existing) return existing;

    // Try cookie fallback (for privacy mode where localStorage is cleared)
    const cookieId = getCookie(ANONYMOUS_ID_KEY);
    if (cookieId) {
      // Restore to localStorage if possible
      try { localStorage.setItem(ANONYMOUS_ID_KEY, cookieId); } catch { /* ok */ }
      return cookieId;
    }

    const newId = generateId("bl");
    try {
      localStorage.setItem(ANONYMOUS_ID_KEY, newId);
    } catch {
      // localStorage unavailable — fall back to cookie
      setCookie(ANONYMOUS_ID_KEY, newId);
    }
    return newId;
  } catch {
    // localStorage unavailable entirely — use cookie
    try {
      const cookieId = getCookie(ANONYMOUS_ID_KEY);
      if (cookieId) return cookieId;
      const newId = generateId("bl");
      setCookie(ANONYMOUS_ID_KEY, newId);
      return newId;
    } catch {
      return generateId("bl");
    }
  }
}

function getSessionId(): string {
  if (typeof window === "undefined") return "sess_ssr";

  try {
    const existing = sessionStorage.getItem(SESSION_ID_KEY);
    if (existing) return existing;

    const newId = generateId("sess");
    sessionStorage.setItem(SESSION_ID_KEY, newId);
    return newId;
  } catch {
    return generateId("sess");
  }
}

export function getAnalyticsUserId(): string {
  return getAnonymousUserId();
}

type EventName =
  | "page_view"
  | "analysis_created"
  | "analysis_success"
  | "reply_generated"
  | "reply_used"
  | "feedback_given"
  | "return_visit"
  | "relationship_selected"
  | "usage_limit_hit"
  | "image_analysis_started"
  | "share_clicked"
  | "share_image_generated"
  | "share_succeeded"
  | "share_cancelled"
  | "share_reward_granted"
  | "share_reward_limit_hit";

interface TrackProperties {
  [key: string]: string | number | boolean;
}

async function sendTrack(
  eventName: EventName,
  properties?: TrackProperties,
): Promise<void> {
  const anonymousUserId = getAnonymousUserId();
  const sessionId = getSessionId();

  try {
    await fetch(`${API_BASE_URL}/api/v1/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        anonymous_user_id: anonymousUserId,
        event_name: eventName,
        properties: properties ?? null,
        session_id: sessionId,
      }),
    });
  } catch {
    // Silent failure — analytics must never break UX
  }
}

export async function track(
  eventName: EventName,
  properties?: TrackProperties,
): Promise<void> {
  // Dedup check
  const dedupKey = `${eventName}:${JSON.stringify(properties ?? {})}`;
  const now = Date.now();
  const lastSent = recentEvents.get(dedupKey);
  if (lastSent && now - lastSent < DEDUP_WINDOW_MS) return;

  recentEvents.set(dedupKey, now);
  // Clean old entries periodically
  if (recentEvents.size > 100) {
    for (const [key, ts] of recentEvents) {
      if (now - ts > DEDUP_WINDOW_MS) recentEvents.delete(key);
    }
  }

  // Fire and forget
  sendTrack(eventName, properties);
}
