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

/** Always returns "en" on server, reads localStorage on client */
function readSavedLocale(): LocaleKey {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("chatcoach-locale") as LocaleKey | null;
    if (saved === "en" || saved === "zh") return saved;
  }
  return "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  // Always start with "en" on first render (both server & client)
  const [locale, setLocaleState] = useState<LocaleKey>("en");
  const [ready, setReady] = useState(false);

  // On mount, restore the saved locale
  useEffect(() => {
    const saved = readSavedLocale();
    if (saved !== "en") {
      setLocaleState(saved);
    }
    setReady(true);
  }, []);

  const setLocale = useCallback((key: LocaleKey) => {
    setLocaleState(key);
    if (typeof window !== "undefined") {
      localStorage.setItem("chatcoach-locale", key);
      document.documentElement.lang = key === "zh" ? "zh-CN" : "en";
    }
  }, []);

  const toggleLocale = useCallback(() => {
    setLocaleState((prev) => {
      const next = prev === "en" ? "zh" : "en";
      if (typeof window !== "undefined") {
        localStorage.setItem("chatcoach-locale", next);
        document.documentElement.lang = next === "zh" ? "zh-CN" : "en";
      }
      return next;
    });
  }, []);

  const t = locales[locale];

  return (
    <I18nContext.Provider value={{ locale, t, setLocale, toggleLocale }}>
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
