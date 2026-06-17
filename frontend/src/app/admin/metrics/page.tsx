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

interface ErrorCase {
  id: number;
  analysis_id: string;
  reason: string;
  comment: string;
  chat_status: string;
  conversation_stage: string;
  other_style: string;
  user_issue: string;
  created_at: string;
}

interface ErrorCaseStats {
  total_errors: number;
  reason_distribution: Record<string, number>;
  stage_error_distribution: Record<string, number>;
}

const PAGE_SIZE = 20;

export default function DashboardPage() {
  const { t } = useI18n();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [stats, setStats] = useState<ErrorCaseStats | null>(null);
  const [cases, setCases] = useState<ErrorCase[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE_URL}/api/v1/metrics`).then((r) => r.json()),
      fetch(`${API_BASE_URL}/api/v1/quality/stats`).then((r) => r.json()),
      fetch(`${API_BASE_URL}/api/v1/quality/errors?limit=${PAGE_SIZE}&offset=0`).then((r) => r.json()),
    ])
      .then(([metricsData, statsData, casesData]) => {
        setMetrics(metricsData);
        setStats(statsData);
        setCases(casesData.cases || []);
        setTotal(casesData.total || 0);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  const fetchPage = (newPage: number) => {
    const offset = newPage * PAGE_SIZE;
    fetch(`${API_BASE_URL}/api/v1/quality/errors?limit=${PAGE_SIZE}&offset=${offset}`)
      .then((r) => r.json())
      .then((data) => {
        setCases(data.cases || []);
        setTotal(data.total || 0);
        setPage(newPage);
      })
      .catch(() => setError(true));
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500 text-sm">{t.dashboard.fetchError}</p>
      </div>
    );
  }

  if (loading || !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-400 text-sm">{t.dashboard.loading}</p>
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

  const reasonLabels: Record<string, string> = {
    inaccurate: t.feedback.negativeReasons.inaccurate,
    awkward: t.feedback.negativeReasons.awkward,
    tooGeneric: t.feedback.negativeReasons.tooGeneric,
    notMyCase: t.feedback.negativeReasons.notMyCase,
    confusing: t.feedback.negativeReasons.confusing,
    other: t.feedback.negativeReasons.other,
  };

  const cards: { label: string; desc: string; value: string; target?: string }[] = [
    { label: t.dashboard.dau, desc: t.dashboard.dauDesc, value: String(metrics.dau) },
    { label: t.dashboard.d1Retention, desc: t.dashboard.d1RetentionDesc, value: `${metrics.d1_retention}%`, target: "> 20%" },
    { label: t.dashboard.d7Retention, desc: t.dashboard.d7RetentionDesc, value: `${metrics.d7_retention}%`, target: "> 8%" },
    { label: t.dashboard.totalAnalyses, desc: t.dashboard.totalAnalysesDesc, value: String(metrics.total_analyses) },
    { label: t.dashboard.helpfulRate, desc: t.dashboard.helpfulRateDesc, value: `${metrics.helpful_rate}%`, target: "> 50%" },
    { label: t.dashboard.replyAdoptionRate, desc: t.dashboard.replyAdoptionRateDesc, value: `${metrics.reply_adoption_rate}%`, target: "> 30%" },
    { label: t.dashboard.avgAnalysesPerUser, desc: t.dashboard.avgAnalysesPerUserDesc, value: String(metrics.analysis_count_per_user), target: "> 2" },
    { label: t.dashboard.avgAnalysisDuration, desc: t.dashboard.avgAnalysisDurationDesc, value: formatDuration(metrics.avg_analysis_duration_ms), target: "< 30s" },
    { label: t.dashboard.avgOcrDuration, desc: t.dashboard.avgOcrDurationDesc, value: formatDuration(metrics.avg_ocr_duration_ms), target: "< 10s" },
    { label: t.dashboard.shareConversionRate, desc: t.dashboard.shareConversionRateDesc, value: `${metrics.share_conversion_rate}%`, target: "> 30%" },
    { label: t.dashboard.shareClicked, desc: t.dashboard.shareClickedDesc, value: String(metrics.share_clicked_count) },
    { label: t.dashboard.shareSucceeded, desc: t.dashboard.shareSucceededDesc, value: String(metrics.share_succeeded_count) },
  ];

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const sortedReasons = Object.entries(stats?.reason_distribution || {}).sort((a, b) => b[1] - a[1]);
  const maxReasonCount = sortedReasons.length > 0 ? sortedReasons[0][1] : 1;

  return (
    <div className="min-h-screen bg-white p-6 md:p-10 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-900 mb-8">{t.dashboard.title}</h1>

      {/* Core Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-10">
        {cards.map((card) => (
          <div key={card.label} className="border border-gray-200 rounded-xl p-4 flex flex-col">
            <p className="text-xs text-gray-400 mb-1">{card.label}</p>
            <p className="text-2xl font-semibold text-gray-900">{card.value}</p>
            <p className="text-xs text-gray-400 mt-1">{card.desc}</p>
            {card.target && (
              <p className="text-xs text-blue-500 mt-1">Target: {card.target}</p>
            )}
          </div>
        ))}
      </div>

      {/* Quality Section */}
      {stats && (
        <>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 border-t border-gray-100 pt-6">
            {t.dashboard.qualityTitle}
          </h2>

          {/* Quality Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
            <div className="border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{t.dashboard.totalErrors}</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.total_errors}</p>
              <p className="text-xs text-gray-400 mt-1">{t.dashboard.totalErrorsDesc}</p>
            </div>
            <div className="border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{t.dashboard.topReasons}</p>
              {sortedReasons.slice(0, 3).map(([reason, count]) => (
                <p key={reason} className="text-sm text-gray-700">
                  {reasonLabels[reason] || reason}: {count}
                </p>
              ))}
              <p className="text-xs text-gray-400 mt-1">{t.dashboard.topReasonsDesc}</p>
            </div>
            <div className="border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{t.dashboard.stageDistribution}</p>
              {Object.entries(stats.stage_error_distribution || {}).map(([stage, count]) => (
                <p key={stage} className="text-sm text-gray-700">
                  {stage}: {count}
                </p>
              ))}
              <p className="text-xs text-gray-400 mt-1">{t.dashboard.stageDistributionDesc}</p>
            </div>
          </div>

          {/* Reason Bar Chart */}
          {sortedReasons.length > 0 && (
            <div className="mb-8">
              <h3 className="text-sm font-medium text-gray-600 mb-3">{t.dashboard.topReasons}</h3>
              <div className="space-y-2">
                {sortedReasons.map(([reason, count]) => {
                  const width = Math.max(3, (count / maxReasonCount) * 100);
                  return (
                    <div key={reason} className="flex items-center gap-3">
                      <span className="text-xs text-gray-500 w-24 shrink-0 text-right">
                        {reasonLabels[reason] || reason}
                      </span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                        <div
                          className="h-full bg-red-400 rounded-full transition-all"
                          style={{ width: `${width}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 w-8 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error Case List */}
          <div>
            <h3 className="text-sm font-medium text-gray-600 mb-3">
              {t.dashboard.caseList} ({total})
            </h3>

            {cases.length === 0 ? (
              <div className="border border-gray-200 rounded-xl p-8 text-center">
                <p className="text-sm text-gray-400">{t.dashboard.noData}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {cases.map((c) => (
                  <div key={c.id} className="border border-gray-200 rounded-xl p-4 text-sm">
                    <div className="flex flex-wrap gap-x-6 gap-y-1 text-gray-500 mb-2">
                      <span>
                        <span className="text-gray-400">{t.dashboard.analysisId}:</span>{" "}
                        {c.analysis_id || "–"}
                      </span>
                      <span>
                        <span className="text-gray-400">{t.dashboard.chatStatus}:</span>{" "}
                        {c.chat_status || "–"}
                      </span>
                      <span>
                        <span className="text-gray-400">{t.dashboard.time}:</span>{" "}
                        {c.created_at || "–"}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-2 mb-2">
                      {c.conversation_stage && (
                        <span className="inline-block rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-xs text-blue-700">
                          {t.dashboard.conversationStage}: {c.conversation_stage}
                        </span>
                      )}
                      {c.other_style && (
                        <span className="inline-block rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-xs text-indigo-700">
                          {t.dashboard.otherStyle}: {c.other_style}
                        </span>
                      )}
                      {c.user_issue && (
                        <span className="inline-block rounded-full bg-red-50 border border-red-200 px-2.5 py-0.5 text-xs text-red-700">
                          {t.dashboard.userIssue}: {c.user_issue}
                        </span>
                      )}
                    </div>

                    <p className="text-gray-700">
                      <span className="text-gray-400">{t.dashboard.errorReason}:</span>{" "}
                      {c.reason
                        ? c.reason.split(",").map((r) => reasonLabels[r.trim()] || r.trim()).join(", ")
                        : "–"}
                    </p>
                    {c.comment && (
                      <p className="text-gray-500 mt-1">
                        <span className="text-gray-400">{t.dashboard.userComment}:</span>{" "}
                        {c.comment}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-6">
                <button
                  onClick={() => fetchPage(page - 1)}
                  disabled={page === 0}
                  className="px-4 py-2 text-sm border border-gray-200 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  {t.dashboard.prev}
                </button>
                <span className="text-sm text-gray-400">
                  {t.dashboard.page.replace("{page}", String(page + 1))}
                </span>
                <button
                  onClick={() => fetchPage(page + 1)}
                  disabled={page >= totalPages - 1}
                  className="px-4 py-2 text-sm border border-gray-200 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  {t.dashboard.next}
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
