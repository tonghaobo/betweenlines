interface StatusBadgeProps {
  status: string;
}

const statusConfig: Record<string, { bg: string; text: string; icon: string }> = {
  "积极互动": {
    bg: "bg-green-50 border-green-200",
    text: "text-green-700",
    icon: "🟢",
  },
  "普通互动": {
    bg: "bg-blue-50 border-blue-200",
    text: "text-blue-700",
    icon: "🔵",
  },
  "礼貌回应": {
    bg: "bg-yellow-50 border-yellow-200",
    text: "text-yellow-700",
    icon: "🟡",
  },
  "偏冷淡": {
    bg: "bg-orange-50 border-orange-200",
    text: "text-orange-700",
    icon: "🟠",
  },
  "对话风险较高": {
    bg: "bg-red-50 border-red-200",
    text: "text-red-700",
    icon: "🔴",
  },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig["普通互动"];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-semibold border ${config.bg} ${config.text}`}
    >
      <span>{config.icon}</span>
      {status}
    </span>
  );
}
