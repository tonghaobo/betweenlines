"use client";

import { useState } from "react";
import { submitOutcome } from "@/lib/api";
import { track } from "@/lib/analytics";
import { useI18n } from "@/contexts/I18nContext";

const ADOPTION_OPTIONS = ["sent", "modified", "notSent"] as const;

export function ReplyAdoptionCard() {
  const { t } = useI18n();
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!selected || submitting) return;
    setSubmitting(true);

    // Track reply_used
    if (selected !== "notSent") {
      track("reply_used", { reply_type: selected });
    }

    try {
      await submitOutcome(selected);
      if (selected !== "notSent") {
        const followUpKey = "betweenlines_followup";
        const existing = JSON.parse(localStorage.getItem(followUpKey) || "[]");
        existing.push({ timestamp: Date.now() });
        localStorage.setItem(followUpKey, JSON.stringify(existing));
      }
    } catch {
      // Silently fail
    }
    setSubmitted(true);
  };

  if (submitted) {
    return null;
  }

  return (
    <div className="w-full max-w-2xl card animate-slide-up">
      <p className="text-gray-600 text-sm text-center mb-4">{t.adoption.question}</p>
      <div className="flex flex-wrap justify-center gap-3">
        {ADOPTION_OPTIONS.map((option) => {
          const label = t.adoption[option as keyof typeof t.adoption] as string;
          const isSelected = selected === option;
          return (
            <button
              key={option}
              onClick={() => setSelected(option)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 border ${
                isSelected
                  ? "bg-blue-50 border-blue-300 text-blue-700 ring-2 ring-blue-200"
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
            className="px-8 py-2.5 rounded-xl text-sm font-medium bg-blue-600 text-white
                       hover:bg-blue-700 transition-all duration-200 disabled:opacity-50
                       disabled:cursor-not-allowed"
          >
            {submitting ? "..." : "OK"}
          </button>
        </div>
      )}
    </div>
  );
}
