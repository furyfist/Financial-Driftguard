import type { Regime } from "../types"

const config: Record<Regime, { label: string; color: string; dot: string; pulse: boolean }> = {
  stable:       { label: "Stable",        color: "bg-stable-soft text-stable border-stable/20",         dot: "bg-stable",   pulse: false },
  credit_stress:{ label: "Credit stress", color: "bg-warning-soft text-warning border-warning/20",       dot: "bg-warning",  pulse: true  },
  rate_shock:   { label: "Rate shock",    color: "bg-warning-soft text-warning border-warning/20",       dot: "bg-warning",  pulse: true  },
  recession:    { label: "Recession",     color: "bg-critical-soft text-critical border-critical/20",    dot: "bg-critical", pulse: true  },
  black_swan:   { label: "Black swan",    color: "bg-critical-soft text-critical border-critical/20",    dot: "bg-critical", pulse: true  },
  unknown:      { label: "Unknown",       color: "bg-border-subtle text-ink-muted border-border",        dot: "bg-ink-faint",pulse: false },
}

export function RegimeBadge({ regime }: { regime: Regime | null }) {
  const r = regime ?? "unknown"
  const c = config[r]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-mono font-medium ${c.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${c.pulse ? "pulse-dot" : ""}`} />
      {c.label}
    </span>
  )
}