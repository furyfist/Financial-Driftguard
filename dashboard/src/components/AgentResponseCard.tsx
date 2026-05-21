import type { Action, Regime } from "../types"
import { RegimeBadge } from "./RegimeBadge"

// ── Severity derived from action ──────────────────────────────────────────────

type SeverityTier = "low" | "medium" | "high" | "critical"

const ACTION_SEVERITY: Record<string, SeverityTier> = {
  proceed:              "low",
  monitor:              "low",
  proceed_with_caution: "medium",
  investigate:          "high",
  champion_challenger:  "high",
  retrain:              "high",
  freeze:               "critical",
  escalate:             "critical",
  halt:                 "critical",
}

const SEVERITY_STYLES: Record<SeverityTier, { pill: string; bar: string; impact: string }> = {
  low:      { pill: "bg-stable-soft text-stable border-stable/20",     bar: "bg-stable",   impact: "Low" },
  medium:   { pill: "bg-warning-soft text-warning border-warning/20",   bar: "bg-warning",  impact: "Medium" },
  high:     { pill: "bg-warning-soft text-warning border-warning/20",   bar: "bg-warning",  impact: "High" },
  critical: { pill: "bg-critical-soft text-critical border-critical/20", bar: "bg-critical", impact: "Critical" },
}

const ACTION_LABELS: Record<string, string> = {
  monitor:              "Monitor",
  proceed:              "Proceed",
  investigate:          "Investigate",
  proceed_with_caution: "Caution",
  champion_challenger:  "A/B Compare",
  retrain:              "Retrain",
  freeze:               "Freeze",
  escalate:             "Escalate",
  halt:                 "Halt",
}

// ── Typing animation dots ──────────────────────────────────────────────────────

function TypingDots() {
  return (
    <div className="flex gap-1 items-center h-4">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-ink-faint animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  )
}

// ── Component ──────────────────────────────────────────────────────────────────

interface AgentResponseCardProps {
  regime?:         Regime | null
  action?:         Action
  confidence?:     number      // 0–1
  recommendation:  string
  sources?:        string[]
  loading?:        boolean
}

export function AgentResponseCard({
  regime,
  action,
  confidence = 0,
  recommendation,
  sources = [],
  loading = false,
}: AgentResponseCardProps) {
  const severity = ACTION_SEVERITY[action ?? "monitor"] ?? "low"
  const styles   = SEVERITY_STYLES[severity]
  const confPct  = Math.round(confidence * 100)

  if (loading) {
    return (
      <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-3">
        <TypingDots />
      </div>
    )
  }

  return (
    <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-4 space-y-3">

      {/* Top row: regime badge + severity pill + confidence bar */}
      <div className="flex items-center gap-2 flex-wrap">
        {regime && <RegimeBadge regime={regime} />}
        {action && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border font-mono text-xs font-semibold ${styles.pill}`}>
            {ACTION_LABELS[action] ?? action} — {styles.impact}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <div className="w-24 h-1.5 bg-border-subtle rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${styles.bar}`}
              style={{ width: `${confPct}%` }}
            />
          </div>
          <span className="font-mono text-xs text-ink-faint tabular-nums">{confPct}%</span>
        </div>
      </div>

      {/* Recommendation body */}
      <p className="text-ink leading-relaxed" style={{ fontSize: "16px", fontWeight: 700 }}>
        {recommendation}
      </p>

      {/* Impact box */}
      <div className="bg-[#F7F6F3] border border-border-subtle rounded-md px-3 py-2">
        <p className="font-mono text-xs text-ink-muted">
          Estimated impact: <span className="font-semibold text-ink">{styles.impact}</span>
        </p>
      </div>

      {/* Source chips */}
      {sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {sources.map((src, i) => (
            <span
              key={i}
              className="font-mono text-[10px] bg-border-subtle border border-border rounded px-2 py-0.5 text-ink-muted"
            >
              {src}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
