import { ChatAnalysisResponse } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { AnalysisCard } from "./AnalysisCard";
import { ReplySuggestions } from "./ReplySuggestions";
import { TimingAdvice } from "./TimingAdvice";
import { useI18n } from "@/contexts/I18nContext";

interface ResultPageProps {
  data: ChatAnalysisResponse;
}

export function ResultPage({ data }: ResultPageProps) {
  const { t } = useI18n();

  return (
    <div className="w-full max-w-2xl space-y-8 animate-fade-in">
      <div className="flex flex-col items-center space-y-3">
        <p className="text-xs text-gray-400 uppercase tracking-widest">
          {t.result.chatStatus}
        </p>
        <StatusBadge status={data.chat_status} />
      </div>

      <AnalysisCard
        analysis={data.analysis}
        issues={data.issues}
        risks={data.risks}
      />

      <ReplySuggestions suggestions={data.reply_suggestions} />

      <TimingAdvice advice={data.timing_advice} />
    </div>
  );
}
