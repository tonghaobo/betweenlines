import { useI18n } from "@/contexts/I18nContext";

export function HeroSection() {
  const { t } = useI18n();

  return (
    <div className="flex flex-col items-center text-center space-y-4 py-12">
      {/* Badge */}
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-700/10">
        {t.hero.badge}
      </span>

      {/* Main title */}
      <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
        {t.hero.title1}
        <br />
        <span className="text-blue-600">{t.hero.title2}</span>
      </h1>

      {/* Subtitle */}
      <p className="text-lg text-gray-500 max-w-lg">
        {t.hero.subtitle}
      </p>

      {/* Three features */}
      <div className="flex flex-wrap justify-center gap-6 pt-4 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          {t.hero.feature1}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          {t.hero.feature2}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          {t.hero.feature3}
        </div>
      </div>
    </div>
  );
}
