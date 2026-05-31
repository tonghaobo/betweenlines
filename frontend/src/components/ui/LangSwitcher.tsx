import { useI18n } from "@/contexts/I18nContext";

export default function LangSwitcher() {
  const { locale, toggleLocale } = useI18n();

  return (
    <button
      onClick={toggleLocale}
      className="fixed top-4 right-4 z-50 flex items-center gap-1.5 rounded-full border border-gray-300 bg-white/80 px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm backdrop-blur-sm transition-all hover:bg-white hover:shadow-md"
      aria-label={locale === "en" ? "切换到中文" : "Switch to English"}
    >
      <span className={locale === "en" ? "font-semibold text-blue-600" : "text-gray-400"}>EN</span>
      <span className="text-gray-300">/</span>
      <span className={locale === "zh" ? "font-semibold text-blue-600" : "text-gray-400"}>中文</span>
    </button>
  );
}
