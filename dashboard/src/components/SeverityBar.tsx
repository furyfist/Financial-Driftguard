import type { Severity } from "../types"

const widths: Record<Severity, string> = {
  none: "w-[8%]", low: "w-[30%]", medium: "w-[55%]", high: "w-[78%]", critical: "w-full"
}
const colors: Record<Severity, string> = {
  none: "bg-stable", low: "bg-stable", medium: "bg-warning", high: "bg-accent", critical: "bg-critical"
}

export function SeverityBar({ severity, score }: { severity: Severity; score: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1 bg-border-subtle rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${widths[severity]} ${colors[severity]}`} />
      </div>
      <span className={`font-mono text-xs tabular-nums ${score > 0.25 ? "text-critical" : score > 0.10 ? "text-warning" : "text-stable"}`}>
        {score.toFixed(4)}
      </span>
    </div>
  )
}