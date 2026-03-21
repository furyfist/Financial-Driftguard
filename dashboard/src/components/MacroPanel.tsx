import { useEffect, useState } from "react"
import type { MacroSnapshot } from "../types"
import { macroApi } from "../api/client"
import { RegimeBadge } from "./RegimeBadge"

interface MacroMetric {
  label: string
  value: number | null
  format: (v: number) => string
  status: (v: number) => "ok" | "warn" | "critical"
}

export function MacroPanel() {
  const [macro, setMacro]     = useState<MacroSnapshot | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    macroApi.latest()
      .then(setMacro)
      .catch(() => setMacro(null))
      .finally(() => setLoading(false))
  }, [])

  const metrics: MacroMetric[] = [
    {
      label:  "VIX",
      value:  macro?.vix ?? null,
      format: v => v.toFixed(2),
      status: v => v > 35 ? "critical" : v > 23 ? "warn" : "ok",
    },
    {
      label:  "Credit spread",
      value:  macro?.credit_spread ?? null,
      format: v => `${v.toFixed(2)}%`,
      status: v => v > 3.5 ? "critical" : v > 2.8 ? "warn" : "ok",
    },
    {
      label:  "Yield curve",
      value:  macro?.yield_curve ?? null,
      format: v => `${v.toFixed(2)}%`,
      status: v => v < 0 ? "critical" : v < 0.5 ? "warn" : "ok",
    },
    {
      label:  "Fed funds",
      value:  macro?.fed_funds_rate ?? null,
      format: v => `${v.toFixed(2)}%`,
      status: v => v > 4.5 ? "warn" : "ok",
    },
  ]

  const statusColor = {
    ok:       "text-stable",
    warn:     "text-warning",
    critical: "text-critical",
  }

  return (
    <div className="bg-surface border border-border rounded-lg">
      <div className="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="font-display font-medium text-sm text-ink">
            Live macro signals
          </h2>
          {macro && (
            <RegimeBadge regime={macro.regime} />
          )}
        </div>
        {macro && (
          <span className="font-mono text-xs text-ink-faint">
            {new Date(macro.fetched_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-4 gap-0 divide-x divide-border-subtle">
          {[1,2,3,4].map(i => (
            <div key={i} className="p-4">
              <div className="h-3 bg-border-subtle rounded animate-pulse mb-2 w-16" />
              <div className="h-6 bg-border-subtle rounded animate-pulse w-12" />
            </div>
          ))}
        </div>
      ) : !macro ? (
        <div className="px-5 py-4 text-ink-faint font-mono text-xs">
          No macro data — check FRED_API_KEY in .env
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-0 divide-x divide-border-subtle">
          {metrics.map(m => {
            const s = m.value !== null ? m.status(m.value) : "ok"
            return (
              <div key={m.label} className="p-4">
                <p className="text-xs text-ink-faint mb-1">{m.label}</p>
                <p className={`font-mono font-medium text-lg ${statusColor[s]}`}>
                  {m.value !== null ? m.format(m.value) : "—"}
                </p>
              </div>
            )
          })}
        </div>
      )}

      {macro?.regime_confidence !== null && macro?.regime_confidence !== undefined && (
        <div className="px-5 py-3 border-t border-border-subtle">
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-faint">Classifier confidence</span>
            <div className="flex-1 h-1 bg-border-subtle rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-500"
                style={{ width: `${(macro.regime_confidence * 100).toFixed(0)}%` }}
              />
            </div>
            <span className="font-mono text-xs text-ink-muted">
              {(macro.regime_confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      )}
    </div>
  )
}