"use client";

import { useState, useRef, useCallback, useEffect, type DragEvent } from "react";
import { useI18n } from "@/contexts/I18nContext";
import { analyzeScreenshot, getUsage, type ScreenshotAnalysisResponse, type UsageInfo, type RelationshipType } from "@/lib/api";
import { getAnalyticsUserId, track } from "@/lib/analytics";
import { RelationshipSelector } from "./RelationshipSelector";

interface ChatInputProps {
  onSubmit: (text: string, relationshipType: RelationshipType, source?: string) => void;
  isLoading: boolean;
  initialText?: string;
  relationshipType: RelationshipType;
  onRelationshipChange: (type: RelationshipType) => void;
}

type InputMode = "text" | "screenshot";

export function ChatInput({ onSubmit, isLoading, initialText = "", relationshipType, onRelationshipChange }: ChatInputProps) {
  const { t } = useI18n();
  const [mode, setMode] = useState<InputMode>("text");

  // Text mode state
  const [text, setText] = useState(() => {
    if (typeof window === "undefined") return initialText;
    try {
      const saved = sessionStorage.getItem("betweenlines_draft_text");
      return saved || initialText;
    } catch { return initialText; }
  });
  const [charCount, setCharCount] = useState(initialText.length);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync example text from parent
  useEffect(() => {
    if (initialText) {
      setText(initialText);
      setCharCount(initialText.length);
      setMode("text");
      setExtractedText(null);
      setSelectedFile(null);
      setScreenshotError(null);
      setScreenshotCount(0);
    }
  }, [initialText]);

  // Screenshot mode state
  const [dragOver, setDragOver] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractedText, setExtractedText] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const saved = sessionStorage.getItem("betweenlines_ocr_text");
      if (saved) {
        const data = JSON.parse(saved);
        if (Date.now() - data.timestamp < 30 * 60 * 1000) return data.text;
      }
    } catch { /* ok */ }
    return null;
  });
  const [screenshotError, setScreenshotError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [screenshotCount, setScreenshotCount] = useState(() => {
    if (typeof window === "undefined") return 0;
    try {
      const saved = sessionStorage.getItem("betweenlines_ocr_count");
      return saved ? parseInt(saved, 10) || 0 : 0;
    } catch { return 0; }
  });
  const screenshotCountRef = useRef(screenshotCount);
  useEffect(() => { screenshotCountRef.current = screenshotCount; }, [screenshotCount]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Usage tracking
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const refreshUsage = useCallback(async () => {
    try {
      const anonymousUserId = getAnalyticsUserId();
      const info = await getUsage(anonymousUserId);
      setUsage(info);
    } catch {
      // Silently fail
    }
  }, []);

  // Fetch usage on mount and after analysis
  useEffect(() => {
    refreshUsage();
  }, [refreshUsage]);

  const MAX_CHARS = usage?.max_chat_length ?? 2000;
  const MIN_CHARS = 10;
  const MAX_SCREENSHOTS = usage?.max_screenshots_per_request ?? 3;

  // Track relationship selection (only on change)
  const prevRelationshipRef = useRef(relationshipType);
  useEffect(() => {
    if (prevRelationshipRef.current !== relationshipType) {
      prevRelationshipRef.current = relationshipType;
      track("relationship_selected", { relationship_type: relationshipType });
    }
  }, [relationshipType]);

  // --- Text mode handlers ---
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= MAX_CHARS) {
      setText(value);
      setCharCount(value.length);
      try { sessionStorage.setItem("betweenlines_draft_text", value); } catch { /* ok */ }
    }
  };

  const handleSubmit = () => {
    if (text.trim().length >= MIN_CHARS && !isLoading) {
      try { sessionStorage.removeItem("betweenlines_draft_text"); } catch { /* ok */ }
      onSubmit(text.trim(), relationshipType);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isValid = text.trim().length >= MIN_CHARS;
  const isOverLimit = charCount > MAX_CHARS;

  // --- Screenshot mode handlers ---
  const validateFile = (file: File): string | null => {
    const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      return "不支持的文件格式，请上传 PNG、JPEG 或 WebP 图片。";
    }
    if (file.size > 10 * 1024 * 1024) {
      return "图片大小超过 10MB，请压缩后再上传。";
    }
    return null;
  };

  /** Compress image to reduce upload size and speed up vision model processing */
  const compressImage = async (file: File): Promise<File> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(url);
        const maxDim = 1280;
        let { width, height } = img;
        if (width > maxDim || height > maxDim) {
          const ratio = Math.min(maxDim / width, maxDim / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) { resolve(file); return; }
        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            if (!blob) { resolve(file); return; }
            resolve(new File([blob], file.name, { type: "image/jpeg", lastModified: file.lastModified }));
          },
          "image/jpeg",
          0.6,
        );
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  };

  const processScreenshot = useCallback(async (files: File[]) => {
    // Check cumulative total (use ref for latest value, avoids stale closure)
    if (screenshotCountRef.current + files.length > MAX_SCREENSHOTS) {
      setScreenshotError(t.chatInput.maxScreenshotsError.replace("{max}", String(MAX_SCREENSHOTS)));
      return;
    }
    for (const file of files) {
      const error = validateFile(file);
      if (error) {
        setScreenshotError(error);
        return;
      }
    }

    // Sort by capture timestamp (lastModified) to preserve chronological order
    const sorted = [...files].sort((a, b) => a.lastModified - b.lastModified);

    setScreenshotError(null);
    setSelectedFile(sorted.length === 1 ? sorted[0] : null);
    setExtracting(true);

    track("image_analysis_started", { file_count: sorted.length });
    const ocrStartTime = Date.now();

    try {
      // Compress images before upload (reduces model processing time)
      const compressed = await Promise.all(sorted.map(compressImage));
      const anonymousUserId = getAnalyticsUserId();
      const result: ScreenshotAnalysisResponse = await analyzeScreenshot(compressed, anonymousUserId);
      track("image_analysis_success", { duration_ms: Date.now() - ocrStartTime, file_count: sorted.length });
      // Use callback forms to ensure latest state
      setExtractedText((prev) => {
        const merged = prev ? `${prev}\n---\n${result.extracted_text}` : result.extracted_text;
        try {
          sessionStorage.setItem("betweenlines_ocr_text", JSON.stringify({ text: merged, timestamp: Date.now() }));
        } catch { /* ok */ }
        return merged;
      });
      setScreenshotCount((prev) => {
        const newCount = prev + sorted.length;
        try { sessionStorage.setItem("betweenlines_ocr_count", String(newCount)); } catch { /* ok */ }
        return newCount;
      });
      refreshUsage();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "截图分析失败";
      setScreenshotError(msg);
      setSelectedFile(null);
    } finally {
      setExtracting(false);
    }
  }, [MAX_SCREENSHOTS, t, refreshUsage]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (fileList && fileList.length > 0) {
      processScreenshot(Array.from(fileList));
    }
    e.target.value = "";
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const fileList = e.dataTransfer.files;
    if (fileList && fileList.length > 0) {
      processScreenshot(Array.from(fileList));
    }
  };

  const handlePaste = useCallback((e: ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const imageFiles: File[] = [];
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith("image/")) {
        e.preventDefault();
        const file = items[i].getAsFile();
        if (file) imageFiles.push(file);
      }
    }
    if (imageFiles.length > 0) {
      processScreenshot(imageFiles);
    }
  }, [processScreenshot]);

  // Global paste listener: works even when focus is not on the drop zone
  useEffect(() => {
    if (mode !== "screenshot" || extracting) return;

    const onPaste = (e: globalThis.ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imageFiles: File[] = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith("image/")) {
          e.preventDefault();
          const file = items[i].getAsFile();
          if (file) imageFiles.push(file);
        }
      }
      if (imageFiles.length > 0) processScreenshot(imageFiles);
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [mode, extracting, processScreenshot]);

  const handleConfirmExtracted = () => {
    if (extractedText && !isLoading) {
      try { sessionStorage.removeItem("betweenlines_ocr_text"); sessionStorage.removeItem("betweenlines_ocr_count"); } catch { /* ok */ }
      onSubmit(extractedText.trim(), relationshipType, "screenshot");
    }
  };

  const handleAddMoreScreenshots = () => {
    fileInputRef.current?.click();
  };

  const handleCancelExtract = () => {
    setExtractedText(null);
    setSelectedFile(null);
    setScreenshotError(null);
    setScreenshotCount(0);
    try { sessionStorage.removeItem("betweenlines_ocr_text"); sessionStorage.removeItem("betweenlines_ocr_count"); } catch { /* ok */ }
  };

  const switchMode = (newMode: InputMode) => {
    setMode(newMode);
    setExtractedText(null);
    setSelectedFile(null);
    setScreenshotError(null);
  };

  return (
    <div className="w-full max-w-lg space-y-3">
      {/* Relationship selector */}
      <RelationshipSelector value={relationshipType} onChange={onRelationshipChange} />

      {/* Mode switcher tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => switchMode("text")}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            mode === "text"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {t.chatInput.analyze}
        </button>
        <button
          onClick={() => switchMode("screenshot")}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            mode === "screenshot"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {t.chatInput.uploadScreenshot}
        </button>
      </div>

      {/* Text input mode */}
      {mode === "text" && (
        <>
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder={t.chatInput.placeholder}
              className={`w-full h-44 p-4 border rounded-xl resize-none
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         text-gray-700 placeholder:text-gray-400 text-sm leading-relaxed
                         transition-shadow duration-200 ${
                           isOverLimit ? "border-red-300" : "border-gray-200"
                         }`}
            />
            <div className={`absolute bottom-3 right-3 text-xs ${isOverLimit ? "text-red-500" : "text-gray-400"}`}>
              {t.chatInput.charCount
                .replace("{current}", String(charCount))
                .replace("{max}", String(MAX_CHARS))}
            </div>
          </div>

          {text.length > 0 && !isValid && (
            <p className="text-xs text-amber-600">
              {t.chatInput.minCharsError.replace("{min}", String(MIN_CHARS))}
            </p>
          )}

          {isOverLimit && (
            <p className="text-xs text-red-500">
              {t.chatInput.maxCharsError.replace("{max}", String(MAX_CHARS))}
            </p>
          )}

          <button
            onClick={handleSubmit}
            disabled={!isValid || isLoading || isOverLimit}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <LoadingSpinner />
                {t.chatInput.analyzing}
              </>
            ) : (
              t.chatInput.analyze
            )}
          </button>

          <p className="text-xs text-gray-400 text-center">
            {t.chatInput.press}{" "}
            <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">⌘</kbd>
            + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">{t.chatInput.enter}</kbd>{" "}
            {t.chatInput.toSubmit}
          </p>

          {/* Daily usage indicator — unified quota for text & screenshot */}
          {usage && (
            <div className="space-y-1">
              <p className={`text-xs text-center ${usage.analysis_used >= (usage.analysis_limit + usage.analysis_reward) ? "text-amber-600 font-medium" : "text-gray-400"}`}>
                {t.chatInput.usageSummary
                  .replace("{used}", String(usage.analysis_used))
                  .replace("{limit}", String(usage.analysis_limit + usage.analysis_reward))
                }
              </p>
              {usage.share_reward_enabled && (
                <p className="text-xs text-center text-blue-500">
                  {usage.share_rewards_used_today >= usage.max_share_rewards_per_day
                    ? t.chatInput.shareExhaustedHint
                    : t.chatInput.shareRewardHint.replace("{remaining}", String(usage.max_share_rewards_per_day - usage.share_rewards_used_today))
                  }
                </p>
              )}
            </div>
          )}
        </>
      )}

      {/* Screenshot upload mode */}
      {mode === "screenshot" && (
        <>
          {/* Hidden file input — position off-viewport, not clipped, so click() works everywhere */}
          <input
            ref={fileInputRef}
            id="screenshot-file-input"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            onChange={handleFileSelect}
            className="fixed top-0 -left-96 opacity-0"
            tabIndex={-1}
          />

          {!extractedText && (
            <>
              {/* Drop zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`w-full h-44 flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl cursor-pointer transition-all
                  ${dragOver
                    ? "border-blue-400 bg-blue-50"
                    : "border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100"
                  }
                  ${extracting ? "pointer-events-none opacity-60" : ""}
                  ${isLoading ? "pointer-events-none opacity-50" : ""}
                `}
              >
                {extracting ? (
                  <>
                    <LoadingSpinner />
                    <span className="text-sm text-gray-500">{t.chatInput.extracting}</span>
                  </>
                ) : (
                  <>
                    <svg
                      className="w-10 h-10 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                    <div className="text-center">
                      <p className="text-sm text-gray-600">{t.chatInput.dragOrClick}</p>
                      <p className="text-xs text-gray-400 mt-1">{t.chatInput.supportedFormats}</p>
                      {MAX_SCREENSHOTS > 1 && (
                        <p className="text-xs text-gray-400">{t.chatInput.maxScreenshotsHint.replace("{max}", String(MAX_SCREENSHOTS))}</p>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Screenshot error */}
              {screenshotError && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                  {screenshotError}
                </div>
              )}

              {/* Paste support for screenshots */}
              <p className="text-xs text-gray-400 text-center">
                {t.chatInput.pasteHint}
              </p>

              {/* Screenshot usage indicator — same unified quota */}
              {usage && (
                <div className="space-y-1">
                  <p className={`text-xs text-center ${usage.analysis_used >= (usage.analysis_limit + usage.analysis_reward) ? "text-amber-600 font-medium" : "text-gray-400"}`}>
                    {t.chatInput.usageSummary
                      .replace("{used}", String(usage.analysis_used))
                      .replace("{limit}", String(usage.analysis_limit + usage.analysis_reward))
                    }
                  </p>
                  {usage.share_reward_enabled && (
                    <p className="text-xs text-center text-blue-500">
                      {usage.share_rewards_used_today >= usage.max_share_rewards_per_day
                        ? t.chatInput.shareExhaustedHint
                        : t.chatInput.shareRewardHint.replace("{remaining}", String(usage.max_share_rewards_per_day - usage.share_rewards_used_today))
                      }
                    </p>
                  )}
                </div>
              )}
            </>
          )}

          {/* Extracted text confirmation */}
          {extractedText && !extracting && (
            <div className="space-y-3">
              <p className="text-sm text-gray-600">{t.chatInput.extractedPreview}</p>
              <textarea
                value={extractedText}
                onChange={(e) => {
                  setExtractedText(e.target.value);
                  try {
                    sessionStorage.setItem("betweenlines_ocr_text", JSON.stringify({ text: e.target.value, timestamp: Date.now() }));
                  } catch { /* ok */ }
                }}
                className="w-full p-4 border border-gray-200 rounded-xl bg-gray-50 text-sm text-gray-700
                           leading-relaxed max-h-60 resize-none focus:outline-none focus:border-blue-300"
                rows={5}
              />
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  <button
                    onClick={handleCancelExtract}
                    className="flex-1 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    disabled={isLoading}
                  >
                    {t.chatInput.cancelExtract}
                  </button>
                  <button
                    onClick={handleConfirmExtracted}
                    disabled={isLoading}
                    className="btn-primary flex-1 flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <>
                        <LoadingSpinner />
                        {t.chatInput.analyzing}
                      </>
                    ) : (
                      t.chatInput.confirmAnalyze
                    )}
                  </button>
                </div>
                <label
                  htmlFor="screenshot-file-input"
                  className={`w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center gap-1.5 ${isLoading ? "opacity-50 pointer-events-none" : "cursor-pointer"}`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  {t.chatInput.addMoreScreenshots}
                </label>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
