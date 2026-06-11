"use client";

import { useI18n } from "@/contexts/I18nContext";

export function SocialProof() {
  const { t } = useI18n();

  const quotes = [
    { quote: t.socialProof.quote1, author: t.socialProof.author1 },
    { quote: t.socialProof.quote2, author: t.socialProof.author2 },
    { quote: t.socialProof.quote3, author: t.socialProof.author3 },
  ];

  return (
    <section className="w-full max-w-3xl py-8">
      <h2 className="text-center text-sm font-medium text-gray-400 uppercase tracking-wider mb-6">
        {t.socialProof.heading}
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {quotes.map((item, i) => (
          <div
            key={i}
            className="flex flex-col p-5 rounded-2xl bg-gradient-to-br from-gray-50 to-blue-50/30 
                       border border-gray-100 shadow-sm"
          >
            <p className="text-sm text-gray-600 leading-relaxed italic flex-1">
              {item.quote}
            </p>
            <p className="text-xs text-gray-400 mt-3 font-medium">
              {item.author}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
