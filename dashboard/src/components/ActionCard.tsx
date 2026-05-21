import type { Action, Regime } from "../types"
import { RegimeBadge } from "./RegimeBadge"

// ── Color config by action ─────────────────────────────────────────────────────

type ActionTier = "green" | "amber" | "red"

const TIER: Record<Action, ActionTier> = {
  monitor:              "green",
  proceed:              "green",
  investigate:          "amber",
  proceed_with_caution: "amber",
  champion_challenger:  "amber",
  retrain:              "amber",
  freeze:               "red",
  escalate:             "red",
  halt:                 "red",
}

const TIER_STYLES: Record<ActionTier, { border: string; badge: string; label: string; dot: string }> = {
  green: {
    border: "border-stable/40 bg-stable-soft/30",
    badge:  "bg-stable-soft text-stable border-stable/20",
    label:  "text-stable",
    dot:    "bg-stable",
  },
  amber: {
    border: "border-warning/40 bg-warning-soft/30",
    badge:  "bg-warning-soft text-warning border-warning/20",
    label:  "text-warning",
    dot:    "bg-warning",
  },
  red: {
    border: "border-critical/40 bg-critical-soft/30",
    badge:  "bg-critical-soft text-critical border-critical/20",
    label:  "text-critical",
    dot:    "bg-critical pulse-dot",
  },
}

const ACTION_LABELS: Record<Action, string> = {
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

// ── Component ──────────────────────────────────────────────────────────────────

interface ActionCardProps {
  action:               Action
  confidence:           number          // 0–1
  regime:               Regime | null
  recommendation:       string          // plain-language text from the agent
  topFeatures?:         string[]        // worst-drifting feature names
  featureExplanations?: Record<string, string>  // feature → LLM explanation text
  reasoning?:           string          // agent's internal reasoning (collapsible)
  onAcknowledge?:       () => void      // optional one-click acknowledge callback
}

export function ActionCard({
  action,
  confidence,
  regime,
  recommendation,
  topFeatures = [],
  featureExplanations,
  reasoning,
  onAcknowledge,
}: ActionCardProps) {
  const tier    = TIER[action] ?? "amber"
  const styles  = TIER_STYLES[tier]
  const confPct = Math.round(confidence * 100)

  return (
    <div className={`rounded-lg border px-5 py-4 space-y-3 ${styles.border}`}>

      {/* Header row — action badge + regime + confidence */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-mono font-semibold ${styles.badge}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${styles.dot}`} />
          {ACTION_LABELS[action]}
        </span>

        {regime && <RegimeBadge regime={regime} />}

        <span className="ml-auto font-mono text-xs text-ink-faint tabular-nums">
          {confPct}% confidence
        </span>
      </div>

      {/* Confidence bar */}
      <div className="h-1 bg-border-subtle rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${
            tier === "green" ? "bg-stable" : tier === "amber" ? "bg-warning" : "bg-critical"
          }`}
          style={{ width: `${confPct}%` }}
        />
      </div>

      {/* Recommendation text */}
      <p className="text-sm text-ink leading-relaxed">{recommendation}</p>

      {/* Top drifted features */}
      {topFeatures.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {topFeatures.map(f => (
            <span
              key={f}
              className="font-mono text-xs bg-white/70 border border-border rounded px-2 py-0.5 text-ink-muted"
            >
              {f}
            </span>
          ))}
        </div>
      )}

      {/* Why did these features drift? (expandable explanations) */}
      {featureExplanations && topFeatures.length > 0 && (
        <details className="text-xs text-ink-muted">
          <summary className="cursor-pointer font-mono hover:text-ink select-none">
            Why did these features drift?
          </summary>
          <div className="mt-2 space-y-2 pl-2 border-l border-border-subtle">
            {topFeatures
              .filter(f => featureExplanations[f])
              .map(f => (
                <div key={f}>
                  <span className="font-mono font-bold text-ink">{f}</span>
                  {" — "}
                  <span className="text-ink-muted">{featureExplanations[f]}</span>
                </div>
              ))}
          </div>
        </details>
      )}

      {/* Reasoning (collapsible via details) */}
      {reasoning && (
        <details className="text-xs text-ink-muted">
          <summary className="cursor-pointer font-mono hover:text-ink select-none">
            Show reasoning
          </summary>
          <p className="mt-2 leading-relaxed pl-2 border-l border-border-subtle">{reasoning}</p>
        </details>
      )}

      {/* Acknowledge button */}
      {onAcknowledge && (
        <div className="pt-1">
          <button
            onClick={onAcknowledge}
            className="text-xs font-mono text-ink-faint hover:text-ink border border-border rounded px-3 py-1 transition-colors hover:bg-surface"
          >
            Acknowledge
          </button>
        </div>
      )}
    </div>
  )
}
