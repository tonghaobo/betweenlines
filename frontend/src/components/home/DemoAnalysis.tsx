"use client";

import { useI18n } from "@/contexts/I18nContext";
import { track } from "@/lib/analytics";

interface DemoAnalysisProps {
  onTryMyChat: () => void;
}

export function DemoAnalysis({ onTryMyChat }: DemoAnalysisProps) {
  const { t } = useI18n();

  const handleCTA = () => {
    track("demo_cta_clicked");
    onTryMyChat();
  };

  return (
    <section id="demo-analysis" className="w-full max-w-3xl py-8">
      <h2 className="text-center text-sm font-medium text-gray-400 uppercase tracking-wider mb-6">
        {t.demoAnalysis.heading}
      </h2>

      {/* Two-cards layout: side-by-side on desktop, stacked on mobile */}
      <div className="flex flex-col md:flex-row gap-4 md:gap-6">
        {/* Left: Example Chat */}
        <div className="flex-1 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-5 border border-blue-100/50">
          <h3 className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-4">
            {t.demoAnalysis.exampleLabel}
          </h3>

          {/* Chat bubbles */}
          <div className="space-y-3">
            {/* Her message */}
            <div className="flex justify-start">
              <div className="max-w-[75%] bg-white rounded-2xl rounded-bl-md px-4 py-2.5 shadow-sm border border-gray-100">
                <p className="text-sm text-gray-700">{t.demoAnalysis.messages.her1}</p>
              </div>
            </div>

            {/* Me message */}
            <div className="flex justify-end">
              <div className="max-w-[75%] bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm">
                <p className="text-sm text-white">{t.demoAnalysis.messages.me1}</p>
              </div>
            </div>

            {/* Her message */}
            <div className="flex justify-start">
              <div className="max-w-[75%] bg-white rounded-2xl rounded-bl-md px-4 py-2.5 shadow-sm border border-gray-100">
                <p className="text-sm text-gray-700">{t.demoAnalysis.messages.her2}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Analysis Result */}
        <div className="flex-1 bg-white rounded-2xl p-5 border border-gray-200 shadow-sm">
          <h3 className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-4">
            {t.demoAnalysis.resultLabel}
          </h3>

          <div className="space-y-4">
            {/* Vibe */}
            <div>
              <p className="text-xs text-gray-400 mb-1">{t.demoAnalysis.vibe}</p>
              <p className="text-lg font-semibold text-gray-800">{t.demoAnalysis.vibeLevel}</p>
            </div>

            {/* Status */}
            <div>
              <p className="text-xs text-gray-400 mb-1">{t.demoAnalysis.status}</p>
              <p className="text-sm text-gray-600 leading-relaxed">{t.demoAnalysis.statusText}</p>
            </div>

            {/* Advice */}
            <div>
              <p className="text-xs text-gray-400 mb-1">{t.demoAnalysis.adviceLabel}</p>
              <p className="text-sm text-gray-600 leading-relaxed">{t.demoAnalysis.adviceText}</p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Button */}
      <div className="flex justify-center mt-6">
        <button
          onClick={handleCTA}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white 
                     bg-gradient-to-r from-blue-500 to-blue-600 rounded-full
                     hover:from-blue-600 hover:to-blue-700 
                     shadow-md shadow-blue-500/25 hover:shadow-lg hover:shadow-blue-500/30
                     transition-all duration-200"
        >
          {t.demoAnalysis.cta}
        </button>
      </div>
    </section>
  );
}
