import { useI18n } from "@/contexts/I18nContext";

interface StatusBadgeProps {
  status: string;
}

/** Map backend Chinese status values to i18n keys */
const statusKeyMap: Record<string, keyof typeof import("@/locales/en").default.result.statusLabels> = {
  "积极互动": "positive",
  "普通互动": "normal",
  "礼貌回应": "polite",
  "偏冷淡": "cold",
  "对话风险较高": "highRisk",
};

const statusBgMap: Record<string, string> = {
  positive: "bg-green-50 border-green-200",
  normal: "bg-blue-50 border-blue-200",
  polite: "bg-yellow-50 border-yellow-200",
  cold: "bg-orange-50 border-orange-200",
  highRisk: "bg-red-50 border-red-200",
};

const statusTextMap: Record<string, string> = {
  positive: "text-green-700",
  normal: "text-blue-700",
  polite: "text-yellow-700",
  cold: "text-orange-700",
  highRisk: "text-red-700",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { t } = useI18n();
  const statusKey = statusKeyMap[status] || "normal";
  const label = t.result.statusLabels[statusKey];
  const icon = t.result.statusIcons[statusKey];

  const bg = statusBgMap[statusKey] || statusBgMap.normal;
  const textColor = statusTextMap[statusKey] || statusTextMap.normal;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-semibold border ${bg} ${textColor}`}
    >
      <span>{icon}</span>
      {label}
    </span>
  );
}
