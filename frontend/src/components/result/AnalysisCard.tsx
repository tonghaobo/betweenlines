interface AnalysisCardProps {
  analysis: string;
  issues: string[];
  risks: string[];
}

export function AnalysisCard({ analysis, issues, risks }: AnalysisCardProps) {
  return (
    <div className="card space-y-5 animate-fade-in">
      <div>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Why this status?
        </h3>
        <p className="text-gray-700 leading-relaxed">{analysis}</p>
      </div>

      {issues.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-amber-600 uppercase tracking-wider mb-2">
            Areas to Improve
          </h3>
          <ul className="space-y-1.5">
            {issues.map((issue, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-gray-600"
              >
                <span className="text-amber-500 mt-0.5 flex-shrink-0">•</span>
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {risks.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-red-600 uppercase tracking-wider mb-2">
            ⚠️ Risk Alert
          </h3>
          <ul className="space-y-1">
            {risks.map((risk, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-red-700"
              >
                <span className="text-red-500 mt-0.5 flex-shrink-0">!</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
