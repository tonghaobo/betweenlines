"use client";

import { useState, useEffect } from "react";
import { useI18n } from "@/contexts/I18nContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Metrics {
  dau: number;
  d1_retention: number;
  d7_retention: number;
  total_analyses: number;
  total_image_analyses: number;
  helpful_rate: number;
  reply_adoption_rate: number;
  analysis_count_per_user: number;
  avg_analysis_duration_ms: number;
  avg_ocr_duration_ms: number;
  share_conversion_rate: number;
  share_clicked_count: number;
  share_succeeded_count: number;
}

export default function MetricsPage() {
  const { t } = useI18n();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/metrics`)
      .then((res) => res.json())
      .then((data) => setMetrics(data))
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500 text-sm">{t.metrics.fetchError}</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-400 text-sm">{t.metrics.loading}</p>
      </div>
    );
  }

  const formatDuration = (ms: number): string => {
    if (!ms) return "–";
    const seconds = Math.round(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const cards: { label: string; desc: string; value: string; target?: string }[] = [
    {
      label: t.metrics.dau,
      desc: t.metrics.dauDesc,
      value: String(metrics.dau),
    },
    {
      label: t.metrics.d1Retention,
      desc: t.metrics.d1RetentionDesc,
      value: `${metrics.d1_retention}%`,
      target: "> 20%",
    },
    {
      label: t.metrics.d7Retention,
      desc: t.metrics.d7RetentionDesc,
      value: `${metrics.d7_retention}%`,
      target: "> 8%",
    },
    {
      label: t.metrics.totalAnalyses,
      desc: t.metrics.totalAnalysesDesc,
      value: String(metrics.total_analyses),
    },
    {
      label: t.metrics.helpfulRate,
      desc: t.metrics.helpfulRateDesc,
      value: `${metrics.helpful_rate}%`,
      target: "> 50%",
    },
    {
      label: t.metrics.replyAdoptionRate,
      desc: t.metrics.replyAdoptionRateDesc,
      value: `${metrics.reply_adoption_rate}%`,
      target: "> 30%",
    },
    {
      label: t.metrics.avgAnalysesPerUser,
      desc: t.metrics.avgAnalysesPerUserDesc,
      value: String(metrics.analysis_count_per_user),
      target: "> 2",
    },
    {
      label: t.metrics.avgAnalysisDuration,
      desc: t.metrics.avgAnalysisDurationDesc,
      value: formatDuration(metrics.avg_analysis_duration_ms),
      target: "< 30s",
    },
    {
      label: t.metrics.avgOcrDuration,
      desc: t.metrics.avgOcrDurationDesc,
      value: formatDuration(metrics.avg_ocr_duration_ms),
      target: "< 10s",
    },
    {
      label: t.metrics.shareConversionRate,
      desc: t.metrics.shareConversionRateDesc,
      value: `${metrics.share_conversion_rate}%`,
      target: "> 30%",
    },
    {
      label: t.metrics.shareClicked,
      desc: t.metrics.shareClickedDesc,
      value: String(metrics.share_clicked_count),
    },
    {
      label: t.metrics.shareSucceeded,
      desc: t.metrics.shareSucceededDesc,
      value: String(metrics.share_succeeded_count),
    },
  ];

  return (
    <div className="min-h-screen bg-white p-6 md:p-10 max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-900 mb-8">{t.metrics.title}</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="border border-gray-200 rounded-xl p-4 flex flex-col"
          >
            <p className="text-xs text-gray-400 mb-1">{card.label}</p>
            <p className="text-2xl font-semibold text-gray-900">{card.value}</p>
            <p className="text-xs text-gray-400 mt-1">{card.desc}</p>
            {card.target && (
              <p className="text-xs text-blue-500 mt-1">Target: {card.target}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
