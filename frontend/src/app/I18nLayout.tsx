"use client";

import { useEffect, type ReactNode } from "react";
import { I18nProvider } from "@/contexts/I18nContext";
import LangSwitcher from "@/components/ui/LangSwitcher";

export function I18nLayout({ children }: { children: ReactNode }) {
  useEffect(() => {
    const saved = typeof window !== "undefined"
      ? localStorage.getItem("chatcoach-locale")
      : null;
    document.documentElement.lang = saved === "zh" ? "zh-CN" : "en";
  }, []);

  return (
    <I18nProvider>
      <LangSwitcher />
      {children}
    </I18nProvider>
  );
}
