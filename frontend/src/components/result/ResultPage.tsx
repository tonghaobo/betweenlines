import { ChatAnalysisResponse } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { AnalysisCard } from "./AnalysisCard";
import { ReplySuggestions } from "./ReplySuggestions";
import { TimingAdvice } from "./TimingAdvice";
import { TurningPointCard } from "./TurningPointCard";
import AnalysisTags from "./AnalysisTags";
import { useI18n } from "@/contexts/I18nContext";

interface ResultPageProps {
  data: ChatAnalysisResponse;
  tags?: { conversation_stage: string; other_style: string; user_issue: string } | null;
}

export function ResultPage({ data, tags }: ResultPageProps) {
  const { t } = useI18n();

  return (
    <div className="w-full max-w-2xl space-y-8 animate-fade-in">
      <div className="flex flex-col items-center space-y-3">
        <p className="text-xs text-gray-400 uppercase tracking-widest">
          {t.result.chatStatus}
        </p>
        <StatusBadge status={data.chat_status} />
      </div>

      <TurningPointCard data={data.turning_point} />

      <AnalysisCard
        analysis={data.analysis}
        issues={data.issues}
        risks={data.risks}
      />

      <AnalysisTags tags={tags || null} />

      <ReplySuggestions suggestions={data.reply_suggestions} />

      <TimingAdvice advice={data.timing_advice} />
    </div>
  );
}
