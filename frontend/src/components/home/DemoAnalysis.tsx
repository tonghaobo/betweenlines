"use client";

import { useI18n } from "@/contexts/I18nContext";
import { track } from "@/lib/analytics";
import { PrivacyBadge } from "@/components/ui/PrivacyBadge";

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
      <div className="flex flex-col md:flex-row gap-4 md:gap-6 mb-4">
        {/* Left: Example Chat */}
        <div className="flex-1 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-5 border border-blue-100/50">
          <h3 className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-4">
            {t.demoAnalysis.exampleLabel}
          </h3>

          {/* Chat bubbles */}
          <div className="space-y-3">
            <div className="flex justify-start">
              <div className="max-w-[75%] bg-white rounded-2xl rounded-bl-md px-4 py-2.5 shadow-sm border border-gray-100">
                <p className="text-sm text-gray-700">{t.demoAnalysis.messages.her1}</p>
              </div>
            </div>
            <div className="flex justify-end">
              <div className="max-w-[75%] bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm">
                <p className="text-sm text-white">{t.demoAnalysis.messages.me1}</p>
              </div>
            </div>
            <div className="flex justify-start">
              <div className="max-w-[75%] bg-white rounded-2xl rounded-bl-md px-4 py-2.5 shadow-sm border border-gray-100">
                <p className="text-sm text-gray-700">{t.demoAnalysis.messages.her2}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Full Analysis Result */}
        <div className="flex-1 bg-white rounded-2xl p-5 border border-gray-200 shadow-sm">
          {/* Demo label */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-[10px] font-medium text-amber-600 bg-amber-50 
                             px-2 py-0.5 rounded-full uppercase tracking-wide">
              {t.demoAnalysis.demoLabel}
            </span>
          </div>

          {/* Status Badge */}
          <div className="mb-4">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full 
                            bg-yellow-50 border border-yellow-200">
              <span className="text-base">🟡</span>
              <span className="text-sm font-medium text-yellow-700">
                {t.demoAnalysis.statusText}
              </span>
            </div>
          </div>

          {/* Vibe Level */}
          <div className="mb-4">
            <p className="text-xs text-gray-400 mb-0.5">{t.demoAnalysis.vibe}</p>
            <p className="text-base font-semibold text-gray-800">{t.demoAnalysis.vibeLevel}</p>
          </div>

          {/* Status Why */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-medium text-gray-500 mb-1">
              {t.result.whyThisStatus}
            </p>
            <p className="text-xs text-gray-600 leading-relaxed">
              {t.demoAnalysis.statusWhy}
            </p>
          </div>

          {/* Analysis */}
          <div className="mb-4">
            <p className="text-xs font-medium text-gray-500 mb-1.5">
              {t.demoAnalysis.analysis.title}
            </p>
            <p className="text-xs text-gray-700 leading-relaxed">
              {t.demoAnalysis.analysis.content}
            </p>
          </div>

          {/* Issues */}
          <div className="mb-4 p-3 bg-orange-50 rounded-lg">
            <p className="text-xs font-medium text-orange-600 mb-1">
              {t.result.areasToImprove}
            </p>
            <ul className="text-xs text-orange-700 space-y-0.5">
              {t.demoAnalysis.analysis.issues.map((issue: string, i: number) => (
                <li key={i} className="flex gap-1.5">
                  <span className="flex-shrink-0">•</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Risks */}
          <div className="mb-4 p-3 bg-red-50 rounded-lg">
            <p className="text-xs font-medium text-red-600 mb-1">
              {t.result.riskAlert}
            </p>
            <ul className="text-xs text-red-700 space-y-0.5">
              {t.demoAnalysis.analysis.risks.map((risk: string, i: number) => (
                <li key={i} className="flex gap-1.5">
                  <span className="flex-shrink-0">•</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Turning Point */}
          {t.demoAnalysis.turningPoint.detected && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-xs font-medium text-blue-600 mb-1">
                {t.result.turningPoint.title}
              </p>
              <p className="text-xs text-blue-700 leading-relaxed mb-1.5">
                {t.demoAnalysis.turningPoint.description}
              </p>
              <div className="flex items-center gap-3 text-[10px]">
                <span className="text-blue-500">
                  {t.result.turningPoint.confidence}: {t.demoAnalysis.turningPoint.confidence}%
                </span>
                <span className="text-orange-500">
                  {t.result.turningPoint.riskLevels.medium}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reply Suggestions — full width cards */}
      <div className="space-y-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-800">
          {t.result.suggestedReplies}
        </h3>
        <p className="text-xs text-gray-500 -mt-3">
          {t.result.replyHint}
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          {/* Natural */}
          <div className="bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-xl p-4 
                          border border-blue-200/50">
            <span className="text-[10px] font-medium text-blue-600 bg-blue-100 
                             px-2 py-0.5 rounded-full">
              {t.demoAnalysis.replies.natural.label}
            </span>
            <p className="text-xs text-gray-500 mt-2 mb-2">
              {t.demoAnalysis.replies.natural.desc}
            </p>
            <p className="text-sm text-gray-800 leading-relaxed mb-3 p-2.5 bg-white 
                          rounded-lg border border-blue-100">
              "{t.demoAnalysis.replies.natural.text}"
            </p>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              {t.result.trajectory.title}: {t.demoAnalysis.replies.natural.trajectory}
            </p>
          </div>

          {/* Humorous */}
          <div className="bg-gradient-to-br from-purple-50 to-purple-100/50 rounded-xl p-4 
                          border border-purple-200/50">
            <span className="text-[10px] font-medium text-purple-600 bg-purple-100 
                             px-2 py-0.5 rounded-full">
              {t.demoAnalysis.replies.humorous.label}
            </span>
            <p className="text-xs text-gray-500 mt-2 mb-2">
              {t.demoAnalysis.replies.humorous.desc}
            </p>
            <p className="text-sm text-gray-800 leading-relaxed mb-3 p-2.5 bg-white 
                          rounded-lg border border-purple-100">
              "{t.demoAnalysis.replies.humorous.text}"
            </p>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              {t.result.trajectory.title}: {t.demoAnalysis.replies.humorous.trajectory}
            </p>
          </div>

          {/* Mature */}
          <div className="bg-gradient-to-br from-slate-50 to-slate-100/50 rounded-xl p-4 
                          border border-slate-200/50">
            <span className="text-[10px] font-medium text-slate-600 bg-slate-200 
                             px-2 py-0.5 rounded-full">
              {t.demoAnalysis.replies.mature.label}
            </span>
            <p className="text-xs text-gray-500 mt-2 mb-2">
              {t.demoAnalysis.replies.mature.desc}
            </p>
            <p className="text-sm text-gray-800 leading-relaxed mb-3 p-2.5 bg-white 
                          rounded-lg border border-slate-100">
              "{t.demoAnalysis.replies.mature.text}"
            </p>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              {t.result.trajectory.title}: {t.demoAnalysis.replies.mature.trajectory}
            </p>
          </div>
        </div>
      </div>

      {/* Timing Advice */}
      <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl p-4 
                      border border-indigo-100/50 mb-6">
        <p className="text-xs font-medium text-indigo-600 mb-1.5">
          {t.result.timingAdvice}
        </p>
        <p className="text-xs text-indigo-700 leading-relaxed">
          {t.demoAnalysis.timingAdvice}
        </p>
      </div>

      {/* Privacy Note */}
      <div className="flex justify-center mb-6">
        <PrivacyBadge variant="compact" />
      </div>

      {/* CTA Button */}
      <div className="flex justify-center">
        <button
          onClick={handleCTA}
          className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white 
                     bg-gradient-to-r from-blue-500 to-blue-600 rounded-full
                     hover:from-blue-600 hover:to-blue-700 
                     shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30
                     transition-all duration-200 hover:scale-105"
        >
          {t.demoAnalysis.startCTA}
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </section>
  );
}
