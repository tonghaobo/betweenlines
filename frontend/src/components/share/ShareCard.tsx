"use client";

import { forwardRef } from "react";
import { useI18n } from "@/contexts/I18nContext";
import type { ChatAnalysisResponse, RelationshipType } from "@/lib/api";

/** Map backend Chinese status values to vibe level keys */
const statusToVibe: Record<string, "cold" | "normal" | "warm" | "positive"> = {
  "积极互动": "positive",
  "普通互动": "normal",
  "礼貌回应": "normal",
  "偏冷淡": "cold",
  "对话风险较高": "cold",
};

const vibeEmoji: Record<string, string> = {
  cold: "🧊",
  normal: "😐",
  warm: "🔥",
  positive: "💚",
};

const vibeBg: Record<string, string> = {
  cold: "bg-slate-100",
  normal: "bg-gray-100",
  warm: "bg-amber-50",
  positive: "bg-emerald-50",
};

const vibeBorder: Record<string, string> = {
  cold: "border-slate-300",
  normal: "border-gray-300",
  warm: "border-amber-300",
  positive: "border-emerald-300",
};

const vibeText: Record<string, string> = {
  cold: "text-slate-700",
  normal: "text-gray-700",
  warm: "text-amber-700",
  positive: "text-emerald-700",
};

/** Fun tags based on status */
const funTags: Record<string, string[]> = {
  cold: ["一块正在冷却的暖宝宝 🧊", "读完就想去喝热水 😅", "气氛需要个小火炉 🔥"],
  normal: ["一杯温开水 🥛", "理工男在做需求评审 😭", "两个人在等对方先说话 🤫"],
  warm: ["小火慢炖中 🍲", "对方在偷偷查你朋友圈 👀", "空气中有点甜 🍬"],
  positive: ["甜度超标 🍯", "对方手机不离手就等你的消息 📱", "双向奔赴本人 🏃"],
};

interface ShareCardProps {
  data: ChatAnalysisResponse;
  relationshipType: RelationshipType;
  size: "9:16" | "1:1";
}

export const ShareCard = forwardRef<HTMLDivElement, ShareCardProps>(
  ({ data, relationshipType, size }, ref) => {
    const { t } = useI18n();
    const vibe = statusToVibe[data.chat_status] || "normal";

    // Truncate analysis to 2 lines (~60 chars)
    const analysisShort = data.analysis.length > 60
      ? data.analysis.slice(0, 60) + "..."
      : data.analysis;

    // Get first advice
    const adviceShort = data.timing_advice.length > 40
      ? data.timing_advice.slice(0, 40) + "..."
      : data.timing_advice;

    // Pick a fun tag (deterministic based on status hash)
    const tags = funTags[vibe] || funTags.normal;
    const tagIndex = data.analysis.length % tags.length;
    const funTag = tags[tagIndex];

    const relationshipLabels: Record<string, string> = {
      romantic: t.relationship.romantic,
      friend: t.relationship.friend,
      family: t.relationship.family,
      coworker: t.relationship.coworker,
      other: t.relationship.other,
    };

    const isPortrait = size === "9:16";
    const cardWidth = 360;
    const cardHeight = isPortrait ? 640 : 360;

    if (isPortrait) {
      return (
        <div
          ref={ref}
          style={{ width: cardWidth, height: cardHeight, fontFamily: "system-ui, -apple-system, sans-serif" }}
          className="bg-white flex flex-col items-center justify-between p-8 overflow-hidden"
        >
          {/* Top: Brand */}
          <div className="flex flex-col items-center w-full">
            <p className="text-lg font-bold text-gray-900 tracking-tight">{t.share.cardTitle}</p>
            <p className="text-xs text-gray-400 mt-0.5">{t.share.cardTagline}</p>
          </div>

          {/* Middle: Content */}
          <div className="flex flex-col items-center gap-4 w-full py-6">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span>{t.share.relationship}：</span>
              <span className="font-medium text-gray-700">{relationshipLabels[relationshipType]}</span>
            </div>

            <div className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl border ${vibeBg[vibe]} ${vibeBorder[vibe]}`}>
              <span className="text-2xl">{vibeEmoji[vibe]}</span>
              <div className="text-left">
                <p className="text-[10px] text-gray-400">{t.share.chatVibe}</p>
                <p className={`text-base font-semibold ${vibeText[vibe]}`}>{t.share.vibeLevels[vibe]}</p>
              </div>
            </div>

            <p className="text-sm text-gray-600 text-center leading-relaxed max-w-[280px]">{analysisShort}</p>

            <div className="px-4 py-2 rounded-xl bg-gray-50 border border-gray-100 w-full max-w-[280px]">
              <p className="text-[10px] text-gray-400 mb-0.5">{t.share.advice}</p>
              <p className="text-sm text-gray-700">{adviceShort}</p>
            </div>

            <p className="text-xs text-gray-400 italic text-center">
              {t.share.funTag} {funTag}
            </p>
          </div>

          {/* Bottom: Brand */}
          <div className="flex flex-col items-center gap-0.5">
            <p className="text-[10px] text-gray-300">{t.share.brand}</p>
            <p className="text-[10px] text-gray-300">{t.share.domain}</p>
          </div>
        </div>
      );
    }

    // 1:1 compact layout — left content, right vibe badge
    return (
      <div
        ref={ref}
        style={{ width: cardWidth, height: cardHeight, fontFamily: "system-ui, -apple-system, sans-serif" }}
        className="bg-white flex overflow-hidden"
      >
        {/* Left: Brand + Analysis + Advice */}
        <div className="flex flex-col justify-between p-5 w-[55%] border-r border-gray-100">
          <div>
            <p className="text-sm font-bold text-gray-900 tracking-tight">{t.share.cardTitle}</p>
            <p className="text-[9px] text-gray-400 mt-0.5">{t.share.cardTagline}</p>
          </div>

          <div className="space-y-2.5 my-3">
            <div className="flex items-center gap-1 text-[10px] text-gray-500">
              <span>{t.share.relationship}：</span>
              <span className="font-medium text-gray-700">{relationshipLabels[relationshipType]}</span>
            </div>

            <p className="text-xs text-gray-600 leading-relaxed">{analysisShort}</p>

            <div className="px-2.5 py-1.5 rounded-lg bg-gray-50 border border-gray-100">
              <p className="text-[9px] text-gray-400">{t.share.advice}</p>
              <p className="text-[11px] text-gray-700 leading-snug">{adviceShort}</p>
            </div>
          </div>

          <div className="space-y-0.5">
            <p className="text-[9px] text-gray-300">{t.share.brand}</p>
            <p className="text-[9px] text-gray-300">{t.share.domain}</p>
          </div>
        </div>

        {/* Right: Vibe badge + Fun tag */}
        <div className="flex flex-col items-center justify-center w-[45%] p-5">
          <div className={`flex flex-col items-center gap-1.5 px-4 py-4 rounded-2xl border ${vibeBg[vibe]} ${vibeBorder[vibe]}`}>
            <span className="text-3xl">{vibeEmoji[vibe]}</span>
            <div className="text-center">
              <p className="text-[9px] text-gray-400">{t.share.chatVibe}</p>
              <p className={`text-sm font-semibold ${vibeText[vibe]}`}>{t.share.vibeLevels[vibe]}</p>
            </div>
          </div>

          <p className="text-[10px] text-gray-400 italic text-center mt-3 leading-snug px-2">
            {funTag}
          </p>
        </div>
      </div>
    );
  }
);

ShareCard.displayName = "ShareCard";
