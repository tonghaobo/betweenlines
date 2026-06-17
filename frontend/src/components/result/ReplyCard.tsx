"use client";

import { useState } from "react";
import { useI18n } from "@/contexts/I18nContext";
import type { TrajectoryPrediction } from "@/lib/api";

interface ReplyCardProps {
  style: string;
  label: string;
  description: string;
  content: string;
  trajectory?: TrajectoryPrediction;
  colorClass: string;
  delay: number;
}

const trendEmoji: Record<string, string> = {
  warm_up: "🟢",
  stable: "🟢",
  cool_down: "🟡",
  conversation_end: "🔴",
};

const riskColors: Record<string, string> = {
  low: "bg-green-50 border-green-100 text-green-700",
  medium: "bg-yellow-50 border-yellow-100 text-yellow-700",
  high: "bg-red-50 border-red-100 text-red-600",
};

export function ReplyCard({
  label,
  description,
  content,
  trajectory,
  colorClass,
  delay,
}: ReplyCardProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const tp = t.result.trajectory;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className="card animate-slide-up hover:shadow-md transition-all duration-300 flex flex-col"
      style={{ animationDelay: `${delay}ms`, animationFillMode: "both" }}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <span
            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorClass}`}
          >
            {label}
          </span>
          <p className="text-xs text-gray-400 mt-1">{description}</p>
        </div>
        <button
          onClick={handleCopy}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
            copied
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          {copied ? t.result.copied : t.result.copy}
        </button>
      </div>

      <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 flex-1">
        <p className="text-gray-800 leading-relaxed text-sm">{content}</p>
      </div>

      {/* Trajectory prediction */}
      {trajectory && (
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
          <p className="text-xs text-gray-400 uppercase tracking-wider">
            {tp.title}
          </p>
          <div className="flex items-center gap-2 text-sm">
            <span>{trendEmoji[trajectory.trend] || "🟡"}</span>
            <span className="text-gray-700 font-medium">
              {tp.trends[trajectory.trend] || trajectory.trend}
            </span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs border ${riskColors[trajectory.risk_level] || riskColors.low}`}>
              {tp.risk}: {tp.riskLevels[trajectory.risk_level] || trajectory.risk_level}
            </span>
          </div>
          {trajectory.explanation && (
            <p className="text-xs text-gray-400 leading-relaxed">
              {trajectory.explanation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
