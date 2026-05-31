"use client";

import { useState } from "react";
import { submitFeedback } from "@/lib/api";

export function FeedbackSection() {
  const [voted, setVoted] = useState<boolean | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handleVote = async (helpful: boolean) => {
    setVoted(helpful);
    try {
      await submitFeedback(helpful);
    } catch {
      // 静默失败，不影响用户体验
    }
    setTimeout(() => setSubmitted(true), 300);
  };

  if (submitted) {
    return (
      <div className="w-full max-w-2xl card text-center animate-fade-in">
        <p className="text-gray-500 text-sm">
          {voted ? "🎉" : "😔"} Thanks for your feedback!
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl card text-center animate-slide-up">
      <p className="text-gray-600 mb-4 text-sm">Was this analysis helpful?</p>
      <div className="flex justify-center gap-4">
        <button
          onClick={() => handleVote(true)}
          className={`px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
            voted === true
              ? "bg-green-100 text-green-700 ring-2 ring-green-500"
              : "bg-gray-50 text-gray-600 hover:bg-green-50 hover:text-green-700"
          }`}
        >
          👍 Helpful
        </button>
        <button
          onClick={() => handleVote(false)}
          className={`px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
            voted === false
              ? "bg-red-100 text-red-700 ring-2 ring-red-500"
              : "bg-gray-50 text-gray-600 hover:bg-red-50 hover:text-red-700"
          }`}
        >
          👎 Not helpful
        </button>
      </div>
    </div>
  );
}
