"use client";

import { useState, useRef } from "react";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  isLoading: boolean;
  initialText?: string;
}

export function ChatInput({ onSubmit, isLoading, initialText = "" }: ChatInputProps) {
  const [text, setText] = useState(initialText);
  const [charCount, setCharCount] = useState(initialText.length);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const MAX_CHARS = 5000;
  const MIN_CHARS = 10;

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= MAX_CHARS) {
      setText(value);
      setCharCount(value.length);
    }
  };

  const handleSubmit = () => {
    if (text.trim().length >= MIN_CHARS && !isLoading) {
      onSubmit(text.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isValid = text.trim().length >= MIN_CHARS;

  return (
    <div className="w-full max-w-lg space-y-3">
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`Paste your chat here...
Example format:
A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢`}
          className="w-full h-44 p-4 border border-gray-200 rounded-xl resize-none
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     text-gray-700 placeholder:text-gray-400 text-sm leading-relaxed
                     transition-shadow duration-200"
          disabled={isLoading}
        />
        <div className="absolute bottom-3 right-3 text-xs text-gray-400">
          {charCount}/{MAX_CHARS}
        </div>
      </div>

      {text.length > 0 && !isValid && (
        <p className="text-xs text-amber-600">
          Please enter at least {MIN_CHARS} characters for analysis.
        </p>
      )}

      <button
        onClick={handleSubmit}
        disabled={!isValid || isLoading}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <LoadingSpinner />
            Analyzing...
          </>
        ) : (
          "Analyze Chat"
        )}
      </button>

      <p className="text-xs text-gray-400 text-center">
        Press <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">⌘</kbd>
        + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">Enter</kbd> to submit
      </p>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
