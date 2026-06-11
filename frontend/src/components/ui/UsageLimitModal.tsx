"use client";

import { useMemo } from "react";
import { useI18n } from "@/contexts/I18nContext";

interface UsageLimitModalProps {
  open: boolean;
  onClose: () => void;
}

interface VariantMessage {
  emoji: string;
  title: string;
  subtitle: string;
}

// Rotating fun messages — pick one at random each time modal opens
const messagesEn: VariantMessage[] = [
  {
    emoji: "😅",
    title: "Alright, you've squeezed enough wisdom out of me today",
    subtitle: "Even AI needs a break. I'll be back tomorrow with fresh takes!",
  },
  {
    emoji: "🏃",
    title: "Whoa, slow down there, chat champion!",
    subtitle: "My brain circuits need a nap. Come back tomorrow for round two.",
  },
  {
    emoji: "🎬",
    title: "That's a wrap for today!",
    subtitle: "Even the best scripts need a rewrite break. See you tomorrow!",
  },
  {
    emoji: "🔋",
    title: "Power level: critically low on vibes",
    subtitle: "Recharging overnight. Fresh analysis ready tomorrow morning!",
  },
  {
    emoji: "🍵",
    title: "Tea break — back tomorrow!",
    subtitle: "Good things come to those who wait ~24 hours.",
  },
];

const messagesZh: VariantMessage[] = [
  {
    emoji: "😅",
    title: "今天聊够了！AI 也得喘口气",
    subtitle: "休息一下，明天再来帮你出谋划策～",
  },
  {
    emoji: "🏃",
    title: "等等！你今天的社交训练已经超额完成了",
    subtitle: "给大脑放个假吧，明天继续解锁新技能！",
  },
  {
    emoji: "🎬",
    title: "今日场次已售罄，明天请早",
    subtitle: "好剧不怕等，明天再来～",
  },
  {
    emoji: "🔋",
    title: "电量告急！需要充一晚才能满血复活",
    subtitle: "你社交能量已耗尽，我也一样……明天见！",
  },
  {
    emoji: "🍵",
    title: "泡杯茶歇会，明日再营业",
    subtitle: "物以稀为贵，好分析不赶时间～",
  },
];

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export function UsageLimitModal({ open, onClose }: UsageLimitModalProps) {
  const { locale, t } = useI18n();

  // Pick a random message combo when the modal opens
  const msg = useMemo(() => {
    const pool = locale === "zh" ? messagesZh : messagesEn;
    return pickRandom(pool);
  }, [open, locale]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="text-4xl">{msg.emoji}</div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{msg.title}</h3>
            <p className="text-sm text-gray-500 mt-1.5">{msg.subtitle}</p>
          </div>
          <button
            onClick={onClose}
            className="w-full px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl
                       hover:bg-gray-200 transition-colors"
          >
            {t.usageLimit.backBtn}
          </button>
        </div>
      </div>
    </div>
  );
}
