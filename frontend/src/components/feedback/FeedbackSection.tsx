"use client";

import { useState } from "react";
import { submitFeedback } from "@/lib/api";
import { track } from "@/lib/analytics";
import { useI18n } from "@/contexts/I18nContext";

const NEGATIVE_REASONS = [
  "inaccurate",
  "awkward",
  "tooGeneric",
  "notMyCase",
  "confusing",
  "other",
] as const;

const POSITIVE_REASONS = [
  "attitudeAnalysis",
  "replySuggestion",
  "timingAdvice",
  "riskAlert",
  "authentic",
] as const;

export function FeedbackSection() {
  const { t } = useI18n();
  const [voted, setVoted] = useState<boolean | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleVote = (helpful: boolean) => {
    setVoted(helpful);
    setSelectedReasons([]);
    setComment("");
  };

  const toggleReason = (reason: string) => {
    setSelectedReasons((prev) =>
      prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason],
    );
  };

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);

    // Track feedback_given
    track("feedback_given", { helpful: voted! });

    try {
      await submitFeedback(voted!, undefined, selectedReasons, comment);
    } catch {
      // Silently fail
    }
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="w-full max-w-2xl card text-center animate-fade-in">
        <p className="text-gray-500 text-sm">
          {voted ? "🎉" : "😔"} {t.feedback.thanks}
        </p>
      </div>
    );
  }

  // Step 1: Show thumbs up/down
  if (voted === null) {
    return (
      <div className="w-full max-w-2xl card text-center animate-slide-up">
        <p className="text-gray-600 mb-4 text-sm">{t.feedback.question}</p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => handleVote(true)}
            className="px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 bg-gray-50 text-gray-600 hover:bg-green-50 hover:text-green-700"
          >
            {t.feedback.helpful}
          </button>
          <button
            onClick={() => handleVote(false)}
            className="px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 bg-gray-50 text-gray-600 hover:bg-red-50 hover:text-red-700"
          >
            {t.feedback.notHelpful}
          </button>
        </div>
      </div>
    );
  }

  // Step 2: Show reason selection
  const reasons = voted ? POSITIVE_REASONS : NEGATIVE_REASONS;
  const reasonTexts = voted ? t.feedback.positiveReasons : t.feedback.negativeReasons;

  return (
    <div className="w-full max-w-2xl card animate-slide-up">
      <div className="text-center mb-4">
        <p className="text-gray-600 text-sm">
          {reasonTexts.question}
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-2 mb-4">
        {reasons.map((reason) => {
          const label = reasonTexts[reason as keyof typeof reasonTexts];
          const isSelected = selectedReasons.includes(reason);
          return (
            <button
              key={reason}
              onClick={() => toggleReason(reason)}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 border ${
                isSelected
                  ? voted
                    ? "bg-green-50 border-green-300 text-green-700"
                    : "bg-red-50 border-red-300 text-red-700"
                  : "bg-white border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="mb-4">
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder={t.feedback.commentPlaceholder}
          className="w-full px-4 py-2.5 rounded-lg text-sm border border-gray-200 bg-white
                     focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-transparent
                     placeholder:text-gray-300"
        />
      </div>

      <div className="flex justify-center gap-3">
        <button
          onClick={() => setVoted(null)}
          className="px-5 py-2 rounded-xl text-sm font-medium text-gray-500 hover:text-gray-700
                     transition-colors"
        >
          ←
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="px-8 py-2.5 rounded-xl text-sm font-medium bg-blue-600 text-white
                     hover:bg-blue-700 transition-all duration-200 disabled:opacity-50
                     disabled:cursor-not-allowed"
        >
          {submitting ? "..." : t.feedback.submit}
        </button>
      </div>
    </div>
  );
}
