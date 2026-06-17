import { useI18n } from "@/contexts/I18nContext";
import { ReplyCard } from "./ReplyCard";
import type { ReplySuggestion } from "@/lib/api";

interface ReplySuggestionsProps {
  suggestions: {
    natural: ReplySuggestion;
    humorous: ReplySuggestion;
    mature: ReplySuggestion;
  };
}

type ReplyStyleKey = "natural" | "humorous" | "mature";

const colorClassMap: Record<ReplyStyleKey, string> = {
  natural: "bg-blue-100 text-blue-700",
  humorous: "bg-purple-100 text-purple-700",
  mature: "bg-slate-200 text-slate-700",
};

export function ReplySuggestions({ suggestions }: ReplySuggestionsProps) {
  const { t } = useI18n();

  const replyStyles: { key: ReplyStyleKey }[] = [
    { key: "natural" },
    { key: "humorous" },
    { key: "mature" },
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">
        {t.result.suggestedReplies}
      </h2>
      <p className="text-sm text-gray-500 -mt-2">
        {t.result.replyHint}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {replyStyles.map((style, index) => {
          const suggestion = suggestions[style.key];
          return (
            <ReplyCard
              key={style.key}
              style={style.key}
              label={t.result.replyStyles[style.key]}
              description={t.result.replyStyles[`${style.key}Desc` as keyof typeof t.result.replyStyles] as string}
              content={suggestion?.reply ?? ""}
              trajectory={suggestion?.trajectory}
              colorClass={colorClassMap[style.key]}
              delay={index * 150}
            />
          );
        })}
      </div>
    </div>
  );
}
