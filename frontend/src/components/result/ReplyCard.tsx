"use client";

import { useState } from "react";

interface ReplyCardProps {
  style: string;
  label: string;
  description: string;
  content: string;
  colorClass: string;
  delay: number;
}

export function ReplyCard({
  label,
  description,
  content,
  colorClass,
  delay,
}: ReplyCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className="card animate-slide-up hover:shadow-md transition-all duration-300"
      style={{ animationDelay: `${delay}ms`, animationFillMode: "both" }}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <span
            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorClass}`}
          >
            {label}
          </span>
          <p className="text-xs text-gray-400 mt-1">{description}</p>
        </div>
        <button
          onClick={handleCopy}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
            copied
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>

      <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
        <p className="text-gray-800 leading-relaxed text-sm">{content}</p>
      </div>
    </div>
  );
}
