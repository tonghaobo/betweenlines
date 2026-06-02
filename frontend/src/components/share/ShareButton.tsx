"use client";

import { useState, useRef, useCallback } from "react";
import { toBlob } from "html-to-image";
import { useI18n } from "@/contexts/I18nContext";
import { ShareCard } from "./ShareCard";
import { track, getAnalyticsUserId } from "@/lib/analytics";
import { claimShareReward, type ChatAnalysisResponse, type RelationshipType } from "@/lib/api";

interface ShareButtonProps {
  data: ChatAnalysisResponse;
  relationshipType: RelationshipType;
}

type CardSize = "9:16" | "1:1";
type ShareStatus = "idle" | "generating" | "success" | "cancelled" | "failed";
type ShareMethod = "clipboard" | "native" | "preview" | null;

const SHARE_COUNT_KEY = "betweenlines_share_count";

function getShareCount(): number {
  if (typeof window === "undefined") return 0;
  try {
    return Number(localStorage.getItem(SHARE_COUNT_KEY)) || 0;
  } catch {
    return 0;
  }
}

function incrementShareCount(): number {
  try {
    const count = getShareCount() + 1;
    localStorage.setItem(SHARE_COUNT_KEY, String(count));
    return count;
  } catch {
    return getShareCount();
  }
}

export function ShareButton({ data, relationshipType }: ShareButtonProps) {
  const { t } = useI18n();
  const [cardSize, setCardSize] = useState<CardSize>("9:16");
  const [showCard, setShowCard] = useState(false);
  const [rewardMsg, setRewardMsg] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<ShareStatus>("idle");
  const [shareCount, setShareCount] = useState(getShareCount);
  const [activePlatform, setActivePlatform] = useState<string>("");
  const [lastPlatform, setLastPlatform] = useState<string>("");
  const [lastShareMethod, setLastShareMethod] = useState<ShareMethod>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  const handleOpen = () => {
    track("share_clicked", { relationship_type: relationshipType });
    setShowCard(true);
    setShareStatus("idle");
    setRewardMsg(null);
    setActivePlatform("");
    setLastPlatform("");
    setLastShareMethod(null);
  };

  const generateHash = useCallback((): string => {
    const raw = `${data.chat_status}:${data.analysis.slice(0, 20)}:${new Date().toISOString().slice(0, 10)}`;
    let hash = 0;
    for (let i = 0; i < raw.length; i++) {
      const chr = raw.charCodeAt(i);
      hash = ((hash << 5) - hash) + chr;
      hash |= 0;
    }
    return Math.abs(hash).toString(16).padStart(8, "0");
  }, [data]);

  const generateBlob = async (): Promise<Blob | null> => {
    if (!cardRef.current) return null;
    const blob = await toBlob(cardRef.current, {
      quality: 0.95,
      pixelRatio: 2,
      type: "image/png",
    });
    return blob;
  };

  const onShareSuccess = async (shareType: string, platform?: string, method?: ShareMethod) => {
    const newCount = incrementShareCount();
    setShareCount(newCount);
    setShareStatus("success");
    if (platform) setLastPlatform(platform);
    if (method) setLastShareMethod(method);
    setActivePlatform("");
    track("share_succeeded", { share_type: shareType, platform: platform ?? "" });
    await tryClaimReward(shareType);
  };

  /** Copy image blob to clipboard (Chrome/Edge). Returns true on success. */
  const copyImageToClipboard = async (blob: Blob): Promise<boolean> => {
    if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") return false;
    try {
      // Use blob directly from html-to-image — no canvas round-trip needed
      const clipboardItem = new ClipboardItem({ "image/png": Promise.resolve(blob) });
      await navigator.clipboard.write([clipboardItem]);
      return true;
    } catch (err) {
      console.error("Clipboard write failed:", err);
      return false;
    }
  };

  /** Try native system share sheet (Safari / mobile). Returns true on success. */
  const shareViaNative = async (blob: Blob): Promise<boolean> => {
    if (!navigator.share || !navigator.canShare) {
      console.warn("Native share not available");
      return false;
    }
    try {
      const file = new File([blob], "betweenlines-share.png", { type: "image/png" });
      if (!navigator.canShare({ files: [file] })) {
        console.warn("Native share: files not supported");
        return false;
      }
      await navigator.share({ files: [file], title: "BetweenLines" });
      return true;
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        // User cancelled — treat as handled, not an error
        setShareStatus("cancelled");
        track("share_cancelled", { platform: "native" });
        return true; // "successfully handled" — don't fall through
      }
      console.error("Native share failed:", err);
      return false;
    }
  };

  /** Copy/share image for a specific social platform */
  const handleCopyForPlatform = async (platformKey: string) => {
    setActivePlatform(platformKey);
    setShareStatus("generating");
    setLastPlatform("");
    setLastShareMethod(null);
    setRewardMsg(null);

    try {
      const blob = await generateBlob();
      if (!blob) { setShareStatus("failed"); setActivePlatform(""); return; }

      track("share_image_generated", { size: cardSize, platform: platformKey });

      // Strategy 1: Clipboard write (Chrome/Edge desktop — most common)
      const copied = await copyImageToClipboard(blob);
      if (copied) {
        await onShareSuccess(`platform_${platformKey}`, platformKey, "clipboard");
        return;
      }

      // Strategy 2: Native system share sheet (Safari desktop / mobile browsers)
      const shared = await shareViaNative(blob);
      if (shareStatus === "cancelled") { setActivePlatform(""); return; } // User cancelled
      if (shared) {
        await onShareSuccess(`native_${platformKey}`, platformKey, "native");
        return;
      }

      // Strategy 3: Open image in popup for manual copy (Safari/Firefox fallback)
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "width=600,height=800");
      // Keep URL alive long enough for popup to load, revoke after 60s
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      await onShareSuccess(`preview_${platformKey}`, platformKey, "preview");
    } catch (err) {
      console.error("Share failed:", err);
      setShareStatus("failed");
      setActivePlatform("");
    }
  };

  /** Handle: explicitly download image */
  const handleDownload = useCallback(async () => {
    setShareStatus("generating");
    setActivePlatform("");

    try {
      const blob = await generateBlob();
      if (!blob) { setShareStatus("failed"); return; }

      track("share_image_generated", { size: cardSize });
      downloadBlob(blob);
      await onShareSuccess("save_image");
    } catch (err) {
      console.error("Download failed:", err);
      setShareStatus("failed");
    }
  }, [cardSize, data]);

  const downloadBlob = (blob: Blob) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = "betweenlines-share.png";
    link.href = url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const tryClaimReward = async (shareType: string) => {
    try {
      const userId = getAnalyticsUserId();
      const hash = generateHash();
      const result = await claimShareReward(userId, shareType, hash);

      if (result.granted) {
        track("share_reward_granted", { share_type: shareType });
        setRewardMsg(t.share.rewardGranted);
      } else if (result.message.includes("limit")) {
        track("share_reward_limit_hit", {});
        setRewardMsg(t.share.rewardLimitHit);
      }
    } catch {
      // Silent — reward is optional
    }
  };

  // Status message for user feedback
  const getStatusMessage = (): string | null => {
    switch (shareStatus) {
      case "success":
        if (lastPlatform) {
          const platformName = t.share.platforms[lastPlatform as keyof typeof t.share.platforms] || lastPlatform;
          if (lastShareMethod === "preview") {
            return t.share.openPreviewToCopy.replace("{platform}", platformName);
          }
          if (lastShareMethod === "native") {
            return t.share.shareViaNative;
          }
          // clipboard
          return t.share.copiedAndPaste.replace("{platform}", platformName);
        }
        return t.share.shareDownloaded;
      case "cancelled": return t.share.shareCancelled;
      case "failed": return t.share.shareFailed;
      default: return null;
    }
  };

  const statusMessage = getStatusMessage();

  // Platform definitions
  const platforms = [
    { key: "wechat", icon: "💬", color: "hover:bg-green-50 hover:border-green-300 hover:text-green-700" },
    { key: "xhs", icon: "📕", color: "hover:bg-red-50 hover:border-red-300 hover:text-red-700" },
    { key: "whatsapp", icon: "💚", color: "hover:bg-emerald-50 hover:border-emerald-300 hover:text-emerald-700" },
    { key: "telegram", icon: "✈️", color: "hover:bg-sky-50 hover:border-sky-300 hover:text-sky-700" },
  ];

  if (!showCard) {
    return (
      <button
        onClick={handleOpen}
        className="px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-xl
                   hover:bg-blue-700 transition-colors duration-150 flex items-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
        </svg>
        {t.share.button}
      </button>
    );
  }

  return (
    <div className="w-full max-w-lg space-y-4">
      {/* Size toggle */}
      <div className="flex items-center justify-center gap-2">
        <button
          onClick={() => setCardSize("9:16")}
          className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
            cardSize === "9:16"
              ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
              : "border-gray-200 text-gray-500 hover:bg-gray-50"
          }`}
        >
          {t.share.size916}
        </button>
        <button
          onClick={() => setCardSize("1:1")}
          className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
            cardSize === "1:1"
              ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
              : "border-gray-200 text-gray-500 hover:bg-gray-50"
          }`}
        >
          {t.share.size11}
        </button>
      </div>

      {/* Preview card */}
      <div className="flex justify-center">
        <div className="rounded-xl overflow-hidden shadow-lg border border-gray-100">
          <ShareCard
            ref={cardRef}
            data={data}
            relationshipType={relationshipType}
            size={cardSize}
          />
        </div>
      </div>

      {/* Platform buttons — primary share action */}
      <div className="space-y-2">
        <p className="text-xs text-center text-gray-400">{t.share.shareToSocial}</p>
        <div className="grid grid-cols-4 gap-2">
          {platforms.map(({ key, icon, color }) => (
            <button
              key={key}
              onClick={() => handleCopyForPlatform(key)}
              disabled={shareStatus === "generating"}
              className={`flex flex-col items-center gap-1 px-2 py-3 text-xs font-medium
                         rounded-xl border border-gray-200 text-gray-600 bg-white
                         transition-all duration-150
                         disabled:opacity-60 disabled:cursor-not-allowed
                         ${color} ${activePlatform === key ? "ring-2 ring-blue-300" : ""}
                       `}
            >
              {activePlatform === key && shareStatus === "generating" ? (
                <svg className="animate-spin h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <span className="text-xl">{icon}</span>
              )}
              <span>{t.share.platforms[key as keyof typeof t.share.platforms]}</span>
            </button>
          ))}
        </div>

        {/* Secondary actions: save + close */}
        <div className="flex items-center justify-center gap-3 pt-1">
          <button
            onClick={handleDownload}
            disabled={shareStatus === "generating"}
            className="px-3 py-1.5 text-xs font-medium text-gray-500 bg-gray-50 rounded-lg
                       hover:bg-gray-100 transition-colors disabled:opacity-60 disabled:cursor-not-allowed
                       flex items-center gap-1"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {t.share.saveImage}
          </button>
          <button
            onClick={() => setShowCard(false)}
            className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Share status feedback */}
      {statusMessage && (
        <p className={`text-xs text-center font-medium ${
          shareStatus === "success" ? "text-emerald-600" :
          shareStatus === "cancelled" ? "text-gray-500" :
          "text-red-500"
        }`}>
          {statusMessage}
          {shareStatus === "success" && shareCount > 0 && (
            <span className="text-gray-400 ml-1">({t.share.shareCountLabel}: {shareCount})</span>
          )}
        </p>
      )}

      {/* Reward message */}
      {rewardMsg && (
        <p className="text-xs text-center text-emerald-600 font-medium">
          {rewardMsg}
        </p>
      )}
    </div>
  );
}
