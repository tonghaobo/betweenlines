export function LoadingOverlay() {
  return (
    <div className="flex flex-col items-center justify-center py-20 space-y-6 animate-fade-in">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-blue-100 rounded-full"></div>
        <div className="absolute top-0 left-0 w-16 h-16 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
      </div>
      <div className="text-center space-y-2">
        <p className="text-gray-700 font-medium">Analyzing your chat...</p>
        <p className="text-sm text-gray-400">AI is reading the conversation vibe</p>
      </div>
      <div className="flex gap-2">
        <span className="text-xs text-gray-400 animate-pulse-soft">🔍 Reading messages</span>
      </div>
    </div>
  );
}
