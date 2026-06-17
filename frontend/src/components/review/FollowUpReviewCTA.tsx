"use client";

import { useRouter } from "next/navigation";
import { useI18n } from "@/contexts/I18nContext";

interface Props {
  analysisId?: number;
}

export function FollowUpReviewCTA({ analysisId }: Props) {
  const { t } = useI18n();
  const router = useRouter();
  const r = t.review;

  const handleClick = () => {
    if (analysisId) {
      router.push(`/review?analysis_id=${analysisId}`);
    } else {
      router.push("/review");
    }
  };

  return (
    <div className="w-full max-w-2xl rounded-2xl border border-purple-100 bg-purple-50/50 p-6 space-y-3 animate-fade-in">
      <div className="flex items-start gap-3">
        <span className="text-xl mt-0.5">📋</span>
        <div className="flex-1 space-y-2">
          <p className="text-sm font-semibold text-purple-800">
            {r?.ctaTitle || "回来看看上次的建议有效吗？"}
          </p>
          <p className="text-sm text-purple-600 leading-relaxed">
            {r?.ctaDesc || "把后续对话贴回来，帮你复盘分析。"}
          </p>
        </div>
      </div>
      <button
        onClick={handleClick}
        className="w-full py-2.5 rounded-xl text-sm font-medium text-purple-700
                   bg-white border border-purple-200 hover:bg-purple-100
                   transition-colors"
      >
        {r?.ctaBtn || "上传后续聊天"}
      </button>
    </div>
  );
}
