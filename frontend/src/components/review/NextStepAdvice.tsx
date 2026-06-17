"use client";

import { useI18n } from "@/contexts/I18nContext";

interface Props {
  effectiveness: string;
  advice: string;
}

const effectivenessLabels: Record<string, string> = {
  effective: "上次建议有效",
  partially_effective: "部分有效",
  ineffective: "效果一般",
  cannot_tell: "暂无法判断",
};

const enEffectivenessLabels: Record<string, string> = {
  effective: "Advice was effective",
  partially_effective: "Partially effective",
  ineffective: "Not effective",
  cannot_tell: "Cannot tell yet",
};

export function NextStepAdvice({ effectiveness, advice }: Props) {
  const { t, locale } = useI18n();
  const r = t.review || {};
  const labels = locale === "en" ? enEffectivenessLabels : effectivenessLabels;

  return (
    <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-6 space-y-3">
      {/* Effectiveness */}
      {effectiveness && (
        <div>
          <p className="text-xs text-blue-400 uppercase tracking-wider mb-1">
            {r.adviceEffectiveness || "建议有效性"}
          </p>
          <p className="text-sm text-blue-800 font-medium">
            {labels[effectiveness] || effectiveness}
          </p>
        </div>
      )}

      {/* Next step advice */}
      {advice && (
        <div>
          <p className="text-xs text-blue-400 uppercase tracking-wider mb-1">
            {r.nextStep || "下一步建议"}
          </p>
          <p className="text-sm text-blue-800 leading-relaxed">{advice}</p>
        </div>
      )}
    </div>
  );
}
