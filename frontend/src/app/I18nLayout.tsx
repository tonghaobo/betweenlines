"use client";

import { type ReactNode } from "react";
import { I18nProvider } from "@/contexts/I18nContext";
import LangSwitcher from "@/components/ui/LangSwitcher";

export function I18nLayout({ children }: { children: ReactNode }) {
  return (
    <I18nProvider>
      <LangSwitcher />
      {children}
    </I18nProvider>
  );
}
