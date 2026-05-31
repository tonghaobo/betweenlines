import { useI18n } from "@/contexts/I18nContext";

interface TimingAdviceProps {
  advice: string;
}

export function TimingAdvice({ advice }: TimingAdviceProps) {
  const { t } = useI18n();

  return (
    <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100 animate-slide-up">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
          <span className="text-lg">⏱️</span>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-blue-700 uppercase tracking-wider mb-1">
            {t.result.timingAdvice}
          </h3>
          <p className="text-gray-700 leading-relaxed">{advice}</p>
        </div>
      </div>
    </div>
  );
}
