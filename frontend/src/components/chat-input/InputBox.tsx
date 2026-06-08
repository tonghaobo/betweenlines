"use client";

import { useState, useRef, useCallback, useEffect, type DragEvent } from "react";
import { useI18n } from "@/contexts/I18nContext";
import {
  analyzeChat, analyzeScreenshot, getUsage,
  type ScreenshotAnalysisResponse, type UsageInfo, type RelationshipType,
} from "@/lib/api";
import { getAnalyticsUserId, track } from "@/lib/analytics";
import { RelationshipSelector } from "./RelationshipSelector";

interface InputBoxProps {
  onSubmit: (text: string, relationshipType: RelationshipType) => void;
  isLoading: boolean;
  initialText?: string;
}

export function InputBox({ onSubmit, isLoading, initialText = "" }: InputBoxProps) {
  const { t } = useI18n();
  const [relationshipType, setRelationshipType] = useState<RelationshipType>("romantic");

  // Text state
  const [text, setText] = useState(initialText);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Image extraction state
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
  const [screenshotCount, setScreenshotCount] = useState(() => {
    if (typeof window === "undefined") return 0;
    try {
      const saved = sessionStorage.getItem("betweenlines_ocr_count");
      return saved ? parseInt(saved, 10) || 0 : 0;
    } catch { return 0; }
  });
  // Ref always holds the latest value, avoiding stale closure in async processScreenshots
  const screenshotCountRef = useRef(screenshotCount);
  useEffect(() => { screenshotCountRef.current = screenshotCount; }, [screenshotCount]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Usage tracking
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const refreshUsage = useCallback(async () => {
    try {
      const uid = getAnalyticsUserId();
      const info = await getUsage(uid);
      setUsage(info);
    } catch (err) {
      console.warn("Failed to fetch usage:", err);
      // Show default quota even if API fails
      setUsage({
        analysis_used: 0, analysis_limit: 3, analysis_reward: 0,
        screenshot_used: 0, screenshot_limit: 3,
        max_chat_length: 2000, max_screenshots_per_request: 3,
        share_reward_enabled: false,
      });
    }
  }, []);

  useEffect(() => { refreshUsage(); }, [refreshUsage]);
  useEffect(() => { if (initialText) { setText(initialText); } }, [initialText]);

  const MAX_CHARS = usage?.max_chat_length ?? 2000;

  // ── Text handlers ──
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (e.target.value.length <= MAX_CHARS) setText(e.target.value);
  };

  const handleSubmit = () => {
    if (text.trim().length >= 10 && !isLoading) {
      onSubmit(text.trim(), relationshipType);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  // ── Screenshot compress ──
  const compressImage = async (file: File): Promise<File> => {
    return new Promise((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(url);
        let { width, height } = img;
        const maxDim = 1280;
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
          (blob) => resolve(blob ? new File([blob], file.name, { type: "image/jpeg", lastModified: file.lastModified }) : file),
          "image/jpeg", 0.6,
        );
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  };

  // ── OCR processing ──
  const MAX_SCREENSHOTS = usage?.max_screenshots_per_request ?? 3;

  const processScreenshots = async (files: File[]) => {
    // Check cumulative total (use ref for latest value, avoids stale closure)
    if (screenshotCountRef.current + files.length > MAX_SCREENSHOTS) {
      setScreenshotError(t.chatInput.maxScreenshotsError.replace("{max}", String(MAX_SCREENSHOTS)));
      return;
    }
    setScreenshotError(null);
    setExtracting(true);
    track("image_analysis_started", { file_count: files.length });
    try {
      // Sort by capture time to preserve chronological order
      const sorted = [...files].sort((a, b) => a.lastModified - b.lastModified);
      const compressed = await Promise.all(sorted.map(compressImage));
      const result: ScreenshotAnalysisResponse = await analyzeScreenshot(compressed, getAnalyticsUserId());

      // Use callback forms to ensure we always operate on latest state
      setExtractedText(prev => {
        const merged = prev ? `${prev}\n---\n${result.extracted_text}` : result.extracted_text;
        try {
          sessionStorage.setItem("betweenlines_ocr_text", JSON.stringify({ text: merged, timestamp: Date.now() }));
        } catch { /* ok */ }
        return merged;
      });
      setScreenshotCount(prev => {
        const newCount = prev + sorted.length;
        try { sessionStorage.setItem("betweenlines_ocr_count", String(newCount)); } catch { /* ok */ }
        return newCount;
      });
      refreshUsage();
    } catch (err) {
      setScreenshotError(err instanceof Error ? err.message : "OCR failed");
    } finally {
      setExtracting(false);
    }
  };

  // ── Paste handler (text + image) ──
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
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
      processScreenshots(imageFiles);
    }
    // If text, let default paste behavior handle it → textarea gets the text
  }, []);

  // ── Global paste listener (for when focus is not on textarea) ──
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      // Skip if already handled by React onPaste (textarea) — avoids double OCR
      if (e.defaultPrevented) return;
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
      if (imageFiles.length > 0) processScreenshots(imageFiles);
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, []);

  // ── Drop handlers ──
  const handleDragOver = (e: DragEvent) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = (e: DragEvent) => { e.preventDefault(); setDragOver(false); };
  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) processScreenshots(Array.from(e.dataTransfer.files));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) processScreenshots(Array.from(e.target.files));
    e.target.value = "";
  };

  // ── Extracted text handlers ──
  const handleConfirmExtracted = () => {
    if (extractedText && !isLoading) {
      try { sessionStorage.removeItem("betweenlines_ocr_text"); sessionStorage.removeItem("betweenlines_ocr_count"); } catch { /* ok */ }
      onSubmit(extractedText.trim(), relationshipType);
    }
  };
  const handleCancelExtract = () => {
    setExtractedText(null);
    setScreenshotError(null);
    setScreenshotCount(0);
    try { sessionStorage.removeItem("betweenlines_ocr_text"); sessionStorage.removeItem("betweenlines_ocr_count"); } catch { /* ok */ }
  };
  // ── Render ──
  const showDropZone = !extractedText && !extracting;

  return (
    <div className="w-full max-w-lg space-y-3">
      <RelationshipSelector value={relationshipType} onChange={setRelationshipType} />

      {/* Hidden file input — always rendered, so upload & "add more" buttons work after extraction */}
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

      {/* Unified input area */}
      {showDropZone && (
        <>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative w-full rounded-xl border-2 border-dashed transition-all
              ${dragOver ? "border-blue-400 bg-blue-50" : "border-gray-200 bg-gray-50/50"}`}
          >
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder={t.chatInput.unifiedPlaceholder}
              className="w-full h-40 p-4 bg-transparent resize-none focus:outline-none
                         text-gray-700 placeholder:text-gray-400 text-sm leading-relaxed"
              disabled={isLoading}
              maxLength={MAX_CHARS}
            />
            <div className="absolute bottom-2 right-3 text-xs text-gray-400">
              {text.length}/{MAX_CHARS}
            </div>
          </div>

          {/* Action bar */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleSubmit}
              disabled={text.trim().length < 10 || isLoading}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <LoadingSpinner />
                  {t.chatInput.analyzing}
                </>
              ) : t.chatInput.analyze}
            </button>

            <label
              htmlFor="screenshot-file-input"
              className={`px-3 py-2.5 text-sm font-medium text-gray-500 bg-gray-100 rounded-xl
                         hover:bg-gray-200 transition-colors flex items-center gap-1 ${isLoading ? "opacity-50 pointer-events-none" : "cursor-pointer"}`}
              title={t.chatInput.uploadScreenshot}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </label>
          </div>

          <p className="text-xs text-gray-400 text-center">
            {t.chatInput.pasteHint}
          </p>
        </>
      )}

      {/* Extracting state */}
      {extracting && (
        <div className="flex flex-col items-center gap-3 py-8">
          <LoadingSpinner />
          <p className="text-sm text-gray-500">{t.chatInput.extracting}</p>
          <p className="text-xs text-gray-400">{t.chatInput.extractingHint}</p>
        </div>
      )}

      {/* Extracted text confirmation */}
      {extractedText && !extracting && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">{t.chatInput.extractedPreview}</p>
          <div className="p-4 border border-gray-200 rounded-xl bg-gray-50 text-sm text-gray-700
                          leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
            {extractedText}
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <button onClick={handleCancelExtract}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-600 bg-white
                           border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                disabled={isLoading}>
                {t.chatInput.cancelExtract}
              </button>
              <button onClick={handleConfirmExtracted} disabled={isLoading}
                className="btn-primary flex-1 flex items-center justify-center gap-2">
                {isLoading ? <><LoadingSpinner />{t.chatInput.analyzing}</> : t.chatInput.confirmAnalyze}
              </button>
            </div>
            <label
              htmlFor="screenshot-file-input"
              className={`w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50
                         border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors
                         flex items-center justify-center gap-1.5 ${isLoading ? "opacity-50 pointer-events-none" : "cursor-pointer"}`}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {t.chatInput.addMoreScreenshots}
            </label>
          </div>
        </div>
      )}

      {/* Error */}
      {screenshotError && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {screenshotError}
        </div>
      )}

      {/* Usage indicator */}
      {usage && (
        <p className={`text-xs text-center ${usage.analysis_used >= usage.analysis_limit ? "text-amber-600 font-medium" : "text-gray-400"}`}>
          {t.chatInput.usageSummary
            .replace("{used}", String(usage.analysis_used))
            .replace("{limit}", String(usage.analysis_limit + usage.analysis_reward))}
        </p>
      )}
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
