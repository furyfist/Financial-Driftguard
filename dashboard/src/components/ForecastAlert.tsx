import { useEffect, useState } from "react"
import type { DriftForecast } from "../types"
import { forecastApi } from "../api/client"

interface ForecastAlertProps {
  modelId: string
}

export function ForecastAlert({ modelId }: ForecastAlertProps) {
  const [forecast, setForecast] = useState<DriftForecast | null>(null)

  useEffect(() => {
    forecastApi.get(modelId).then(setForecast).catch(() => {})
  }, [modelId])

  if (!forecast || forecast.probability < 0.5) return null

  const isHigh = forecast.probability >= 0.75
  const pct    = Math.round(forecast.probability * 100)

  return (
    <div
      className={[
        "rounded-lg border px-5 py-4 mb-6 flex items-start gap-3",
        isHigh
          ? "bg-orange-50 border-orange-300 text-orange-900"
          : "bg-yellow-50 border-yellow-300 text-yellow-900",
      ].join(" ")}
    >
      {/* Icon */}
      <span className="text-xl mt-0.5 select-none">{isHigh ? "⚠" : "⚡"}</span>

      {/* Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="font-semibold text-sm">
            Proactive Drift Warning — {pct}% probability
          </span>
          <span
            className={[
              "font-mono text-xs px-2 py-0.5 rounded-full border",
              isHigh
                ? "bg-orange-100 border-orange-200 text-orange-700"
                : "bg-yellow-100 border-yellow-200 text-yellow-700",
            ].join(" ")}
          >
            {forecast.expected_regime}
          </span>
        </div>

        <p className="text-sm opacity-80 leading-snug">{forecast.explanation}</p>

        {forecast.trigger_signals.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {forecast.trigger_signals.map((sig) => (
              <span
                key={sig}
                className="font-mono text-xs bg-white/60 rounded px-1.5 py-0.5 border border-current/10"
              >
                {sig}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Horizon badge */}
      <span className="font-mono text-xs opacity-50 whitespace-nowrap mt-0.5">
        {forecast.horizon_days}d horizon
      </span>
    </div>
  )
}
