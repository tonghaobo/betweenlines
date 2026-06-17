"use client";

import { useState } from "react";
import type { TurningPoint } from "@/lib/api";
import { useI18n } from "@/contexts/I18nContext";

interface TurningPointCardProps {
  data: TurningPoint;
}

export function TurningPointCard({ data }: TurningPointCardProps) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);

  const tp = t.result.turningPoint;

  if (!data) return null;

  return (
    <div className="w-full rounded-2xl border border-gray-100 bg-white p-6 shadow-sm space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <span className="text-xl">
          {data.detected ? "🟡" : "🟢"}
        </span>
        <p className="text-sm font-semibold text-gray-800 uppercase tracking-wider">
          {tp.title}
        </p>
      </div>

      {/* Detection result */}
      <div>
        {data.detected ? (
          <>
            {/* Detected: show turning point details */}
            <p className="text-sm text-gray-500 leading-relaxed">
              {tp.detectedIntro}
            </p>

            {/* Quoted message */}
            {data.quoted_message && (
              <div className="mt-3 rounded-xl bg-yellow-50 border border-yellow-100 px-4 py-3">
                <p className="text-xs text-yellow-700 font-mono whitespace-pre-wrap break-all">
                  {data.quoted_message}
                </p>
              </div>
            )}

            {/* Signal tags */}
            {data.signals.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {data.signals.map((s, i) => (
                  <span
                    key={i}
                    className="inline-block rounded-full bg-orange-50 border border-orange-100 px-2.5 py-0.5 text-xs text-orange-700"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}

            {/* Risk level + confidence */}
            <div className="mt-3 flex items-center gap-2.5 text-xs text-gray-400">
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${
                data.risk_level === "high" ? "bg-red-50 text-red-600" :
                data.risk_level === "medium" ? "bg-yellow-50 text-yellow-700" :
                "bg-green-50 text-green-600"
              }`}>
                {tp.riskLevels[data.risk_level]}
              </span>
              <span>
                {tp.confidence}: {Math.round(data.confidence * 100)}%
              </span>
            </div>

            {/* Explanation with expand/collapse */}
            {data.explanation && (
              <div className="mt-3">
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  {tp.seeWhy}
                  <svg
                    className={`w-3.5 h-3.5 transition-transform ${expanded ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {expanded && (
                  <p className="mt-2 text-sm text-gray-600 leading-relaxed bg-gray-50 rounded-xl px-4 py-3 border border-gray-100">
                    {data.explanation}
                  </p>
                )}
              </div>
            )}

            {/* Disclaimer */}
            <p className="mt-3 text-xs text-gray-300 italic">
              {tp.disclaimer}
            </p>
          </>
        ) : (
          <>
            {/* No turning point detected */}
            <p className="text-sm text-gray-500 leading-relaxed">
              {tp.notDetected || data.explanation || "当前聊天整体比较稳定，没有明显的关系变化信号。"}
            </p>
            <p className="mt-2 text-xs text-gray-300 italic">
              {tp.disclaimer}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
