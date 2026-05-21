import type { Regime } from "../types"

// ── Client-side impact estimate (mirrors backend finsight/impact/estimator.py) ─

const PSI_BANDS: Array<[number, number, number]> = [
  [0.00, 0.10, 0.00],
  [0.10, 0.20, 0.10],
  [0.20, 0.25, 0.20],
  [0.25, Infinity, 0.35],
]

const REGIME_MULTIPLIERS: Record<string, number> = {
  stable:        1.0,
  rate_shock:    1.2,
  credit_stress: 1.5,
  recession:     2.0,
  black_swan:    4.0,
  unknown:       1.3,
}

const BASE_DEFAULT_RATE      = 0.04
const HIGH_RANGE_FACTOR      = 1.5
const DEFAULT_PORTFOLIO_SIZE = 200_000_000   // $200M

function baseFnr(psi: number): number {
  for (const [lo, hi, fnr] of PSI_BANDS) {
    if (psi >= lo && psi < hi) return fnr
  }
  return PSI_BANDS[PSI_BANDS.length - 1][2]
}

export function estimateImpact(
  psiScore: number,
  regime: Regime | null,
  portfolioSize = DEFAULT_PORTFOLIO_SIZE,
): { lowUsd: number; highUsd: number; fnrPct: number } {
  const multiplier = REGIME_MULTIPLIERS[regime ?? "unknown"] ?? 1.3
  const adjusted   = baseFnr(psiScore) * multiplier
  const lowUsd     = portfolioSize * BASE_DEFAULT_RATE * adjusted
  return {
    lowUsd,
    highUsd: lowUsd * HIGH_RANGE_FACTOR,
    fnrPct:  adjusted * 100,
  }
}

// ── Formatting helpers ─────────────────────────────────────────────────────────

function fmt(usd: number): string {
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(1)}M`
  if (usd >= 1_000)     return `$${(usd / 1_000).toFixed(0)}K`
  return usd < 1 ? "<$1" : `$${usd.toFixed(0)}`
}

// ── Component ──────────────────────────────────────────────────────────────────

interface ImpactBannerProps {
  psiScore:       number
  regime:         Regime | null
  portfolioSize?: number        // USD, defaults to $200M
}

export function ImpactBanner({ psiScore, regime, portfolioSize }: ImpactBannerProps) {
  const { lowUsd, highUsd, fnrPct } = estimateImpact(psiScore, regime, portfolioSize)

  // Don't render if there's no material impact
  if (lowUsd < 1) return null

  const isCritical = lowUsd >= 2_000_000

  return (
    <div
      className={[
        "rounded-lg border px-5 py-3 flex items-center gap-4 flex-wrap",
        isCritical
          ? "bg-critical-soft border-critical/30"
          : "bg-warning-soft border-warning/30",
      ].join(" ")}
    >
      {/* Dollar impact */}
      <div className="flex items-baseline gap-1.5">
        <span className={`font-display font-semibold text-base ${isCritical ? "text-critical" : "text-warning"}`}>
          {fmt(lowUsd)}–{fmt(highUsd)}
        </span>
        <span className="text-xs text-ink-muted">estimated exposure</span>
      </div>

      <div className="w-px h-4 bg-border hidden sm:block" />

      {/* FNR increase */}
      <div className="flex items-baseline gap-1">
        <span className={`font-mono text-sm font-medium ${isCritical ? "text-critical" : "text-warning"}`}>
          +{fnrPct.toFixed(0)}%
        </span>
        <span className="text-xs text-ink-muted">FNR increase</span>
      </div>

      <div className="w-px h-4 bg-border hidden sm:block" />

      {/* PSI + regime context */}
      <span className="font-mono text-xs text-ink-faint ml-auto">
        PSI {psiScore.toFixed(4)} · {regime ?? "unknown"} regime
      </span>
    </div>
  )
}
