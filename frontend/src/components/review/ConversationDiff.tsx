"use client";

import type { ConversationChanges } from "@/lib/api";
import { useI18n } from "@/contexts/I18nContext";

interface Props {
  changes: ConversationChanges;
}

const zhLabels: Record<string, string> = {
  initiative: "主动性",
  reply_length: "回复长度",
  emotional_engagement: "情绪表达",
  coldness_risk: "冷场风险",
  topic_continuity: "话题衔接",
};

const enLabels: Record<string, string> = {
  initiative: "Initiative",
  reply_length: "Reply Length",
  emotional_engagement: "Emotional",
  coldness_risk: "Coldness Risk",
  topic_continuity: "Continuity",
};

const dirConfig: Record<string, { icon: string; label: string }> = {
  up: { icon: "↑", label: "上升" },
  down: { icon: "↓", label: "下降" },
  same: { icon: "→", label: "持平" },
};

const enDirConfig: Record<string, { icon: string; label: string }> = {
  up: { icon: "↑", label: "Up" },
  down: { icon: "↓", label: "Down" },
  same: { icon: "→", label: "Same" },
};

export function ConversationDiff({ changes }: Props) {
  const { t, locale } = useI18n();
  const r = t.review || {};
  const labels = locale === "en" ? enLabels : zhLabels;
  const dirs = locale === "en" ? enDirConfig : dirConfig;

  const entries = Object.entries(changes) as [keyof ConversationChanges, string][];
  const hasChanges = entries.some(([, v]) => v !== "same");

  if (!hasChanges) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold text-gray-800 uppercase tracking-wider mb-3">
          {r.changesTitle || "变化维度"}
        </p>
        <p className="text-sm text-gray-400">无明显变化。</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm space-y-3">
      <p className="text-sm font-semibold text-gray-800 uppercase tracking-wider">
        {r.changesTitle || "变化维度"}
      </p>
      <div className="space-y-2">
        {entries.map(([key, value]) => {
          if (value === "same") return null;
          const d = dirs[value] || dirs.same;
          const isUp = value === "up";
          const isDown = value === "down";
          return (
            <div key={key} className="flex items-center justify-between text-sm">
              <span className="text-gray-600">{labels[key] || key}</span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  isUp ? "bg-green-50 text-green-700" :
                  isDown ? "bg-red-50 text-red-700" :
                  "bg-gray-100 text-gray-500"
                }`}
              >
                {d.icon} {d.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
