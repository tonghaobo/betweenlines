"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import en from "@/locales/en";
import zh from "@/locales/zh";
import type { LocaleKey } from "@/locales/types";

/** Use en as the canonical type — zh satisfies the same shape */
type Locale = typeof en;

const locales: Record<LocaleKey, Locale> = { en, zh };

interface I18nContextValue {
  locale: LocaleKey;
  t: Locale;
  setLocale: (key: LocaleKey) => void;
  toggleLocale: () => void;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "betweenlines-locale";

/** 内存 fallback：当 localStorage 不可用时使用 */
let memoryFallback: LocaleKey | null = null;

function isStorageAvailable(): boolean {
  try {
    const testKey = "__storage_test__";
    localStorage.setItem(testKey, testKey);
    localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

let _storageAvailable: boolean | null = null;
function getStorageAvailable(): boolean {
  if (_storageAvailable === null) {
    _storageAvailable = typeof window !== "undefined" && isStorageAvailable();
  }
  return _storageAvailable;
}

function readSavedLocale(): LocaleKey {
  if (typeof window === "undefined") return "en";

  if (getStorageAvailable()) {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as LocaleKey | null;
      if (saved === "en" || saved === "zh") return saved;
    } catch {
      // ignore
    }
  }

  // fallback to memory
  if (memoryFallback === "en" || memoryFallback === "zh") return memoryFallback;

  return "en";
}

function saveLocale(key: LocaleKey): void {
  memoryFallback = key;
  if (getStorageAvailable()) {
    try {
      localStorage.setItem(STORAGE_KEY, key);
    } catch {
      // ignore
    }
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  // 服务端和客户端首次渲染都固定为 "en"，避免 hydration mismatch
  const [locale, setLocaleState] = useState<LocaleKey>("en");
  const [mounted, setMounted] = useState(false);

  // 客户端挂载后从 localStorage 恢复真实语言
  useEffect(() => {
    const saved = readSavedLocale();
    if (saved !== "en") {
      setLocaleState(saved);
    }
    setMounted(true);
  }, []);

  // 同步 html lang 属性
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);

  const setLocale = useCallback((key: LocaleKey) => {
    setLocaleState(key);
    saveLocale(key);
  }, []);

  const toggleLocale = useCallback(() => {
    setLocaleState((prev) => {
      const next = prev === "en" ? "zh" : "en";
      saveLocale(next);
      return next;
    });
  }, []);

  // 挂载前始终用 "en" 渲染，确保和服务端 HTML 完全一致
  const t = locales[mounted ? locale : "en"];

  return (
    <I18nContext.Provider value={{ locale: mounted ? locale : "en", t, setLocale, toggleLocale }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}
