const examples = [
  {
    label: "Casual Chat",
    content: `A: 今天在干嘛呀
B: 刚下班，好累哈哈
A: 辛苦啦，吃饭了吗
B: 还没呢`,
  },
  {
    label: "Short Replies",
    content: `A: 周末有什么安排吗
B: 嗯嗯
A: 最近有部电影还不错
B: 哈哈哈`,
  },
  {
    label: "Getting Cold",
    content: `A: 你平时喜欢做什么呀
B: 没什么特别的
A: 那你喜欢看电影吗
B: 还行`,
  },
];

export function ExampleChats({ onSelect }: { onSelect: (text: string) => void }) {
  return (
    <div className="flex flex-wrap justify-center gap-3 pt-2">
      <span className="text-xs text-gray-400 w-full text-center mb-1">
        Try an example:
      </span>
      {examples.map((ex) => (
        <button
          key={ex.label}
          onClick={() => onSelect(ex.content)}
          className="px-4 py-2 text-sm text-gray-600 bg-gray-50 border border-gray-200 
                     rounded-full hover:bg-gray-100 hover:border-gray-300 
                     transition-colors duration-150"
        >
          {ex.label}
        </button>
      ))}
    </div>
  );
}
