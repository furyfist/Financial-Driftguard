import { useEffect, useState } from "react"
import type { Model, DriftRun } from "../types"
import { driftApi } from "../api/client"
import { RegimeBadge } from "./RegimeBadge"
import { SeverityBar } from "./SeverityBar"

const severityLabel: Record<string, string> = {
  none: "Healthy", low: "Low drift", medium: "Moderate", high: "High drift", critical: "Critical"
}
const severityBorder: Record<string, string> = {
  none: "border-l-stable", low: "border-l-stable", medium: "border-l-warning",
  high: "border-l-accent", critical: "border-l-critical"
}

interface Props { model: Model; onClick: () => void }

export function ModelHealthCard({ model, onClick }: Props) {
  const [run, setRun] = useState<DriftRun | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    driftApi.latest(model.model_id)
      .then(setRun)
      .catch(() => setRun(null))
      .finally(() => setLoading(false))
  }, [model.model_id])

  const severity = run?.overall_severity ?? "none"
  const borderColor = severityBorder[severity]

  return (
    <div
      onClick={onClick}
      className={`bg-surface border border-border border-l-4 ${borderColor} rounded-lg p-5 cursor-pointer hover:shadow-md transition-all duration-200 animate-fade-in`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-display font-semibold text-ink text-sm">{model.model_id}</h3>
          <p className="text-ink-faint text-xs mt-0.5 font-mono">{model.description}</p>
        </div>
        {run && <RegimeBadge regime={run.regime} />}
      </div>

      {loading && (
        <div className="h-8 bg-border-subtle rounded animate-pulse" />
      )}

      {!loading && run && (
        <div className="space-y-2">
          <SeverityBar severity={severity} score={run.drift_score} />
          <div className="flex items-center justify-between">
            <span className={`text-xs font-mono font-medium ${
              severity === "critical" ? "text-critical" :
              severity === "high" ? "text-accent" :
              severity === "medium" ? "text-warning" : "text-stable"
            }`}>
              {severityLabel[severity]}
            </span>
            <span className="text-xs text-ink-faint font-mono">
              {new Date(run.checked_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}

      {!loading && !run && (
        <p className="text-ink-faint text-xs font-mono">No runs yet</p>
      )}
    </div>
  )
}