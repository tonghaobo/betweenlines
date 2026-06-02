"use client";

import { useState, useEffect } from "react";
import { submitOutcome } from "@/lib/api";
import { useI18n } from "@/contexts/I18nContext";

const FOLLOW_UP_KEY = "betweenlines_followup";
const DISMISSED_KEY = "betweenlines_followup_dismissed";
const TWENTY_FOUR_HOURS = 24 * 60 * 60 * 1000;

const OUTCOME_OPTIONS = ["morePositive", "aboutSame", "colder", "noReply", "preferNot"] as const;

export function FollowUpReminder() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    try {
      const dismissed = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
      const entries: { timestamp: number }[] = JSON.parse(
        localStorage.getItem(FOLLOW_UP_KEY) || "[]",
      );

      const now = Date.now();
      const hasEligible = entries.some(
        (entry) =>
          now - entry.timestamp >= TWENTY_FOUR_HOURS &&
          !dismissed.includes(entry.timestamp),
      );

      if (hasEligible) {
        // 延迟 2 秒显示，不干扰页面加载
        const timer = setTimeout(() => setShow(true), 2000);
        return () => clearTimeout(timer);
      }
    } catch {
      // localStorage 异常忽略
    }
  }, []);

  const handleSubmit = async () => {
    if (!selected || submitting) return;
    setSubmitting(true);
    try {
      await submitOutcome("sent", selected);
    } catch {
      // Silently fail
    }
    // 标记所有过期条目为已处理
    try {
      const entries: { timestamp: number }[] = JSON.parse(
        localStorage.getItem(FOLLOW_UP_KEY) || "[]",
      );
      const now = Date.now();
      const dismissed = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
      entries.forEach((entry) => {
        if (now - entry.timestamp >= TWENTY_FOUR_HOURS) {
          dismissed.push(entry.timestamp);
        }
      });
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(dismissed));
    } catch {
      // ignore
    }
    setSubmitted(true);
  };

  const handleDismiss = () => {
    try {
      const entries: { timestamp: number }[] = JSON.parse(
        localStorage.getItem(FOLLOW_UP_KEY) || "[]",
      );
      const now = Date.now();
      const dismissed = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
      entries.forEach((entry) => {
        if (now - entry.timestamp >= TWENTY_FOUR_HOURS) {
          dismissed.push(entry.timestamp);
        }
      });
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(dismissed));
    } catch {
      // ignore
    }
    setShow(false);
  };

  if (!show) return null;

  if (submitted) {
    return (
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-md w-[90%]
                      bg-white rounded-2xl shadow-lg border border-gray-100 p-5 animate-slide-up">
        <p className="text-gray-600 text-sm text-center">{t.feedback.thanks}</p>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-md w-[90%]
                    bg-white rounded-2xl shadow-lg border border-gray-100 p-5 animate-slide-up">
      <button
        onClick={handleDismiss}
        className="absolute top-3 right-3 text-gray-300 hover:text-gray-500 text-lg leading-none"
      >
        ×
      </button>
      <p className="text-gray-700 text-sm font-medium text-center mb-4">
        {t.followUp.question}
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {OUTCOME_OPTIONS.map((option) => {
          const label = t.followUp[option as keyof typeof t.followUp] as string;
          const isSelected = selected === option;
          return (
            <button
              key={option}
              onClick={() => setSelected(option)}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 border ${
                isSelected
                  ? "bg-blue-50 border-blue-300 text-blue-700"
                  : "bg-white border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
      {selected && (
        <div className="flex justify-center mt-4">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-6 py-2 rounded-xl text-sm font-medium bg-blue-600 text-white
                       hover:bg-blue-700 transition-all disabled:opacity-50"
          >
            {submitting ? "..." : "OK"}
          </button>
        </div>
      )}
    </div>
  );
}
