"use client";

import { useI18n } from "@/contexts/I18nContext";

interface PrivacyBadgeProps {
  variant?: "default" | "compact";
}

export function PrivacyBadge({ variant = "default" }: PrivacyBadgeProps) {
  const { t } = useI18n();

  if (variant === "compact") {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        <span>{t.demoAnalysis.privacyNote}</span>
      </div>
    );
  }

  return (
    <div className="w-full max-w-lg mx-auto">
      <div className="flex items-start gap-3 px-4 py-3 rounded-xl 
                      bg-gradient-to-r from-emerald-50 to-teal-50 
                      border border-emerald-200/60">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-100 
                        flex items-center justify-center">
          <svg className="w-4 h-4 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-emerald-800">
            {t.trustSignal.title}
          </p>
          <p className="text-xs text-emerald-700/80 mt-0.5 leading-relaxed">
            {t.trustSignal.description}
          </p>
        </div>
      </div>
    </div>
  );
}
