export function HeroSection() {
  return (
    <div className="flex flex-col items-center text-center space-y-4 py-12">
      {/* Badge */}
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-700/10">
        AI-Powered Chat Analysis
      </span>

      {/* 主标题 */}
      <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
        Understand the vibe
        <br />
        <span className="text-blue-600">before you reply.</span>
      </h1>

      {/* 副标题 */}
      <p className="text-lg text-gray-500 max-w-lg">
        Paste your chat and get instant insight on the conversation mood,
        suggested replies, and timing advice — all in seconds.
      </p>

      {/* 三个卖点 */}
      <div className="flex flex-wrap justify-center gap-6 pt-4 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          No sign-up required
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          Chat data not stored
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-500">✓</span>
          Natural, not PUA
        </div>
      </div>
    </div>
  );
}
