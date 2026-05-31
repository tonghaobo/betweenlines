import { ReplyCard } from "./ReplyCard";

interface ReplySuggestionsProps {
  suggestions: {
    natural: string;
    humorous: string;
    mature: string;
  };
}

const replyStyles = [
  {
    key: "natural" as const,
    label: "自然版",
    description: "最安全，自然不尴尬",
    colorClass: "bg-blue-100 text-blue-700",
  },
  {
    key: "humorous" as const,
    label: "幽默版",
    description: "轻松有趣，带点玩笑",
    colorClass: "bg-purple-100 text-purple-700",
  },
  {
    key: "mature" as const,
    label: "成熟版",
    description: "稳重得体，有边界感",
    colorClass: "bg-slate-200 text-slate-700",
  },
];

export function ReplySuggestions({ suggestions }: ReplySuggestionsProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">
        💬 Suggested Replies
      </h2>
      <p className="text-sm text-gray-500 -mt-2">
        Pick the one that fits your style. All are safe to send.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {replyStyles.map((style, index) => (
          <ReplyCard
            key={style.key}
            style={style.key}
            label={style.label}
            description={style.description}
            content={suggestions[style.key]}
            colorClass={style.colorClass}
            delay={index * 150}
          />
        ))}
      </div>
    </div>
  );
}
