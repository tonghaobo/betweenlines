"use client";

import type { ReviewResponse } from "@/lib/api";
import { useI18n } from "@/contexts/I18nContext";

interface Props {
  data: ReviewResponse;
}

const statusConfig: Record<string, { emoji: string; label: string; color: string }> = {
  improved: { emoji: "🟢", label: "有改善", color: "text-green-700 bg-green-50 border-green-200" },
  similar: { emoji: "🟡", label: "变化不大", color: "text-yellow-700 bg-yellow-50 border-yellow-200" },
  worsened: { emoji: "🔴", label: "有降温风险", color: "text-red-700 bg-red-50 border-red-200" },
  insufficient_data: { emoji: "⚪", label: "数据不足", color: "text-gray-700 bg-gray-50 border-gray-200" },
};

const enStatusConfig: Record<string, { emoji: string; label: string; color: string }> = {
  improved: { emoji: "🟢", label: "Improved", color: "text-green-700 bg-green-50 border-green-200" },
  similar: { emoji: "🟡", label: "Similar", color: "text-yellow-700 bg-yellow-50 border-yellow-200" },
  worsened: { emoji: "🔴", label: "Worsened", color: "text-red-700 bg-red-50 border-red-200" },
  insufficient_data: { emoji: "⚪", label: "Not enough data", color: "text-gray-700 bg-gray-50 border-gray-200" },
};

export function ReviewSummaryCard({ data }: Props) {
  const { t, locale } = useI18n();
  const r = t.review || {};
  const config = (locale === "en" ? enStatusConfig : statusConfig)[data.review_status] || statusConfig.similar;

  return (
    <div className={`rounded-2xl border p-6 ${config.color} space-y-3`}>
      <div className="flex items-center gap-2.5">
        <span className="text-2xl">{config.emoji}</span>
        <p className="text-sm font-semibold uppercase tracking-wider">
          {r.title || "上次建议效果如何？"}
        </p>
      </div>

      <p className="text-lg font-bold">
        {r.statusLabels?.[data.review_status as keyof typeof r.statusLabels] || config.label}
      </p>

      {data.summary && (
        <p className="text-sm leading-relaxed opacity-80">{data.summary}</p>
      )}
    </div>
  );
}
