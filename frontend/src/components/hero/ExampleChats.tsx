import { useI18n } from "@/contexts/I18nContext";

type ExampleKey = "casual" | "shortReplies" | "gettingCold";

const examples: { labelKey: ExampleKey; contentKey: keyof typeof import("@/locales/en").default.exampleChats }[] = [
  { labelKey: "casual", contentKey: "casualContent" },
  { labelKey: "shortReplies", contentKey: "shortRepliesContent" },
  { labelKey: "gettingCold", contentKey: "gettingColdContent" },
];

export function ExampleChats({ onSelect }: { onSelect: (text: string) => void }) {
  const { t } = useI18n();

  return (
    <div className="flex flex-wrap justify-center gap-3 pt-2">
      <span className="text-xs text-gray-400 w-full text-center mb-1">
        {t.exampleChats.label}
      </span>
      {examples.map((ex) => (
        <button
          key={ex.labelKey}
          onClick={() => onSelect(t.exampleChats[ex.contentKey])}
          className="px-4 py-2 text-sm text-gray-600 bg-gray-50 border border-gray-200 
                     rounded-full hover:bg-gray-100 hover:border-gray-300 
                     transition-colors duration-150"
        >
          {t.exampleChats[ex.labelKey]}
        </button>
      ))}
    </div>
  );
}
