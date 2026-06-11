"use client";

import { useI18n } from "@/contexts/I18nContext";
import { track } from "@/lib/analytics";

interface HeroSectionProps {
  onTryFree: () => void;
  onSeeExample: () => void;
}

export function HeroSection({ onTryFree, onSeeExample }: HeroSectionProps) {
  const { t } = useI18n();

  return (
    <div className="flex flex-col items-center text-center space-y-5 py-10 sm:py-14">
      {/* Badge */}
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium 
                       bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-600 ring-1 ring-inset ring-blue-200/50">
        {t.hero.badge}
      </span>

      {/* Main title — single line, emotion-driven */}
      <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl lg:text-5xl">
        {t.hero.title}
      </h1>

      {/* Subtitle — multi-line, action-oriented */}
      <p className="text-base text-gray-500 max-w-md leading-relaxed whitespace-pre-line">
        {t.hero.subtitle}
      </p>

      {/* CTA Buttons */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-3">
        {/* Primary: Try Free */}
        <button
          onClick={() => {
            track("hero_cta_clicked", { cta: "try_free" });
            onTryFree();
          }}
          className="px-6 py-3 text-sm font-semibold text-white 
                     bg-gradient-to-r from-blue-500 to-blue-600 rounded-full
                     hover:from-blue-600 hover:to-blue-700 
                     shadow-md shadow-blue-500/25 hover:shadow-lg hover:shadow-blue-500/30
                     transition-all duration-200"
        >
          {t.hero.ctaTryFree}
        </button>

        {/* Secondary: See Example */}
        <button
          onClick={() => {
            track("hero_cta_clicked", { cta: "see_example" });
            onSeeExample();
          }}
          className="px-6 py-3 text-sm font-medium text-blue-600 
                     bg-blue-50 rounded-full
                     hover:bg-blue-100 transition-colors duration-200"
        >
          {t.hero.ctaSeeExample}
        </button>
      </div>
    </div>
  );
}
