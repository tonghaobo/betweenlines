"use client";

import { useI18n } from "@/contexts/I18nContext";

interface TagsData {
  conversation_stage: string;
  other_style: string;
  user_issue: string;
}

interface AnalysisTagsProps {
  tags: TagsData | null;
}

export default function AnalysisTags({ tags }: AnalysisTagsProps) {
  const { t } = useI18n();

  if (!tags) return null;

  const hasAny = tags.conversation_stage || tags.other_style || tags.user_issue;
  if (!hasAny) return null;

  const tagItems: { key: string; value: string; color: string }[] = [];

  if (tags.conversation_stage) {
    const stageColors: Record<string, string> = {
      "初识": "bg-blue-50 border-blue-200 text-blue-700",
      "熟悉": "bg-green-50 border-green-200 text-green-700",
      "暧昧": "bg-pink-50 border-pink-200 text-pink-700",
      "拉扯": "bg-orange-50 border-orange-200 text-orange-700",
      "冷淡": "bg-gray-50 border-gray-200 text-gray-700",
    };
    tagItems.push({
      key: "conversationStage",
      value: tags.conversation_stage,
      color: stageColors[tags.conversation_stage] || "bg-gray-50 border-gray-200 text-gray-700",
    });
  }

  if (tags.other_style) {
    const styleColors: Record<string, string> = {
      "热情型": "bg-red-50 border-red-200 text-red-700",
      "礼貌型": "bg-indigo-50 border-indigo-200 text-indigo-700",
      "高冷型": "bg-slate-50 border-slate-200 text-slate-700",
      "慢热型": "bg-amber-50 border-amber-200 text-amber-700",
    };
    tagItems.push({
      key: "otherStyle",
      value: tags.other_style,
      color: styleColors[tags.other_style] || "bg-gray-50 border-gray-200 text-gray-700",
    });
  }

  if (tags.user_issue) {
    tagItems.push({
      key: "userIssue",
      value: tags.user_issue,
      color: "bg-red-50 border-red-200 text-red-700",
    });
  }

  // i18n lookup maps
  const stageLabels: Record<string, string> = t.tags?.stages || {};
  const styleLabels: Record<string, string> = t.tags?.styles || {};
  const issueLabels: Record<string, string> = t.tags?.issues || {};

  return (
    <div className="animate-slide-up">
      <div className="flex flex-wrap gap-2">
        {tagItems.map((item) => {
          let label = item.value;
          if (item.key === "conversationStage") {
            label = stageLabels[item.value] || item.value;
          } else if (item.key === "otherStyle") {
            label = styleLabels[item.value] || item.value;
          } else if (item.key === "userIssue") {
            label = issueLabels[item.value] || item.value;
          }

          const prefix =
            item.key === "conversationStage"
              ? t.tags?.conversationStage
              : item.key === "otherStyle"
                ? t.tags?.otherStyle
                : t.tags?.userIssue;

          return (
            <span
              key={item.key}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${item.color}`}
            >
              {prefix && <span className="opacity-60">{prefix}:</span>}
              {label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
