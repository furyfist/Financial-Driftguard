import { useState } from "react"
import type { Alert } from "../types"
import { alertsApi } from "../api/client"

const severityDot: Record<string, string> = {
  low: "bg-stable", medium: "bg-warning", high: "bg-accent", critical: "bg-critical"
}

export function AlertFeed({ alerts, onAck }: { alerts: Alert[]; onAck: () => void }) {
  const [acking, setAcking] = useState<number | null>(null)

  const handleAck = async (id: number) => {
    setAcking(id)
    await alertsApi.acknowledge(id)
    onAck()
    setAcking(null)
  }

  if (alerts.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-ink-faint text-sm font-mono">
        No active alerts
      </div>
    )
  }

  return (
    <div className="divide-y divide-border-subtle">
      {alerts.map((alert, i) => (
        <div
          key={alert.id}
          className="py-3 flex items-start gap-3 animate-fade-in"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div className="mt-1.5 flex-shrink-0">
            <span className={`block w-2 h-2 rounded-full ${severityDot[alert.severity] ?? "bg-ink-faint"} ${alert.severity === "critical" ? "pulse-dot" : ""}`} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-ink leading-relaxed">{alert.message}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs font-mono text-ink-faint">{alert.model_id}</span>
              <span className="text-ink-faint">·</span>
              <span className="text-xs font-mono text-ink-faint">
                {new Date(alert.created_at).toLocaleTimeString()}
              </span>
            </div>
          </div>
          {!alert.acknowledged && (
            <button
              onClick={() => handleAck(alert.id)}
              disabled={acking === alert.id}
              className="flex-shrink-0 text-xs font-mono text-ink-muted hover:text-ink border border-border px-2 py-0.5 rounded transition-colors"
            >
              {acking === alert.id ? "..." : "Ack"}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}