"use client";

import { useI18n } from "@/contexts/I18nContext";
import type { RelationshipType } from "@/lib/api";

interface RelationshipSelectorProps {
  value: RelationshipType;
  onChange: (type: RelationshipType) => void;
}

const RELATIONSHIP_OPTIONS: { key: RelationshipType; icon: string }[] = [
  { key: "romantic", icon: "💕" },
  { key: "friend", icon: "👋" },
  { key: "family", icon: "🏠" },
  { key: "coworker", icon: "💼" },
  { key: "other", icon: "💬" },
];

export function RelationshipSelector({ value, onChange }: RelationshipSelectorProps) {
  const { t } = useI18n();

  return (
    <div className="w-full max-w-lg">
      <p className="text-sm text-gray-500 mb-2">{t.relationship.question}</p>
      <div className="flex flex-wrap gap-2">
        {RELATIONSHIP_OPTIONS.map(({ key, icon }) => (
          <button
            key={key}
            onClick={() => onChange(key)}
            className={`px-3 py-1.5 text-sm rounded-full border transition-all duration-150 ${
              value === key
                ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
                : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50"
            }`}
          >
            <span className="mr-1">{icon}</span>
            {t.relationship[key]}
          </button>
        ))}
      </div>
    </div>
  );
}
