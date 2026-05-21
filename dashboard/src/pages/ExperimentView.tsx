import { useEffect, useState } from "react"
import type { Model, ChallengerResult } from "../types"
import { modelsApi, experimentsApi } from "../api/client"
import { useNavigate } from "react-router-dom"

// ── Winner badge ──────────────────────────────────────────────────────────────

function WinnerBadge({ winner }: { winner: ChallengerResult["winner"] }) {
  const map = {
    challenger_better: { label: "Model Decay Detected",   cls: "bg-red-100 border-red-300 text-red-800" },
    champion_better:   { label: "Champion Stable",         cls: "bg-green-100 border-green-300 text-green-800" },
    inconclusive:      { label: "Inconclusive",            cls: "bg-yellow-100 border-yellow-300 text-yellow-800" },
    no_baseline:       { label: "No Baseline",             cls: "bg-surface border-border text-ink-muted" },
  } as const
  const { label, cls } = map[winner] ?? map.inconclusive
  return (
    <span className={`font-mono text-xs px-2.5 py-1 rounded-full border font-semibold ${cls}`}>
      {label}
    </span>
  )
}

// ── Score cell ────────────────────────────────────────────────────────────────

function ScoreCell({
  label,
  score,
  severity,
  runId,
}: {
  label: string
  score: number | null
  severity: string | null
  runId: number | null
}) {
  const isHigh = severity === "high" || severity === "critical"
  return (
    <div className="bg-canvas border border-border rounded-lg p-4 text-center">
      <p className="font-mono text-xs text-ink-faint mb-1">{label}</p>
      <p className={`font-display text-2xl font-bold ${isHigh ? "text-critical" : "text-ink"}`}>
        {score !== null ? score.toFixed(3) : "—"}
      </p>
      {severity && (
        <p className="font-mono text-xs text-ink-muted mt-1">{severity}</p>
      )}
      {runId !== null && (
        <p className="font-mono text-xs text-ink-faint mt-0.5">run #{runId}</p>
      )}
    </div>
  )
}

// ── Status info panel ─────────────────────────────────────────────────────────

function StatusInfo({ result }: { result: ChallengerResult }) {
  if (result.status === "wrong_regime") {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-800 text-sm">
        <span className="font-semibold">Macro-driven drift — comparison not applicable.</span>{" "}
        {result.recommendation}
      </div>
    )
  }
  if (result.status === "wrong_severity") {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800 text-sm">
        <span className="font-semibold">Drift is low.</span>{" "}
        {result.recommendation}
      </div>
    )
  }
  if (result.status === "insufficient_data" || result.status === "no_baseline") {
    return (
      <div className="bg-surface border border-border rounded-lg p-4 text-ink-muted text-sm">
        {result.recommendation}
      </div>
    )
  }
  return null
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ExperimentView() {
  const [models, setModels]     = useState<Model[]>([])
  const [modelId, setModelId]   = useState<string>("")
  const [result, setResult]     = useState<ChallengerResult | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    modelsApi.list().then(ms => {
      setModels(ms)
      if (ms.length > 0) setModelId(ms[0].model_id)
    }).catch(() => {})
  }, [])

  const fetchResults = () => {
    if (!modelId) return
    setLoading(true)
    setError(null)
    experimentsApi.results(modelId)
      .then(setResult)
      .catch(e => setError(e?.response?.data?.detail ?? "Failed to load results."))
      .finally(() => setLoading(false))
  }

  const runComparison = () => {
    if (!modelId) return
    setLoading(true)
    setError(null)
    experimentsApi.trigger(modelId)
      .then(setResult)
      .catch(e => setError(e?.response?.data?.detail ?? "Comparison failed."))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (modelId) fetchResults()
  }, [modelId])

  return (
    <div className="min-h-screen bg-canvas">
      {/* Header */}
      <header className="bg-surface border-b border-border px-8 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="text-ink-faint hover:text-ink font-mono text-xs transition-colors"
          >
            ← overview
          </button>
          <span className="text-ink-faint font-mono text-xs">/</span>
          <span className="font-display font-semibold text-ink tracking-tight">
            Champion-Challenger
          </span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-8">
        <div className="mb-8">
          <h1 className="font-display font-semibold text-2xl text-ink tracking-tight">
            Champion-Challenger Comparison
          </h1>
          <p className="text-ink-muted text-sm mt-1">
            Compare the current model state against the last stable baseline to detect decay.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 mb-6">
          <select
            value={modelId}
            onChange={e => setModelId(e.target.value)}
            className="bg-surface border border-border rounded-md px-3 py-2 text-sm text-ink font-mono focus:outline-none focus:ring-1 focus:ring-accent"
          >
            {models.map(m => (
              <option key={m.model_id} value={m.model_id}>{m.model_id}</option>
            ))}
          </select>
          <button
            onClick={runComparison}
            disabled={!modelId || loading}
            className="px-4 py-2 bg-accent text-white text-sm font-mono rounded-md hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Running…" : "Run Comparison"}
          </button>
        </div>

        {error && (
          <div className="bg-critical-soft border border-critical/20 rounded-lg px-4 py-3 text-critical text-sm mb-6">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-5">
            {/* Winner + status */}
            <div className="bg-surface border border-border rounded-lg px-5 py-4 flex items-center justify-between gap-4">
              <div>
                <p className="font-mono text-xs text-ink-faint mb-1">Result</p>
                <WinnerBadge winner={result.winner} />
              </div>
              <p className="text-xs font-mono text-ink-faint">
                {new Date(result.triggered_at).toLocaleString()}
              </p>
            </div>

            {/* Non-complete statuses */}
            <StatusInfo result={result} />

            {/* Score comparison (only for completed) */}
            {result.status === "completed" && (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <ScoreCell
                    label="Champion (current)"
                    score={result.champion_drift_score}
                    severity={result.champion_severity}
                    runId={result.champion_run_id}
                  />
                  <div className="flex items-center justify-center">
                    <div className="text-center">
                      <p className="font-mono text-xs text-ink-faint mb-1">Delta</p>
                      <p className={`font-display text-xl font-bold ${
                        (result.drift_score_delta ?? 0) > 0.05 ? "text-critical" : "text-ink-muted"
                      }`}>
                        {result.drift_score_delta !== null
                          ? `${result.drift_score_delta >= 0 ? "+" : ""}${result.drift_score_delta.toFixed(3)}`
                          : "—"}
                      </p>
                    </div>
                  </div>
                  <ScoreCell
                    label="Challenger (baseline)"
                    score={result.challenger_drift_score}
                    severity={result.challenger_severity}
                    runId={result.challenger_run_id}
                  />
                </div>

                {/* Recommendation */}
                <div className="bg-surface border border-border rounded-lg px-5 py-4">
                  <p className="font-mono text-xs text-ink-faint mb-2">Recommendation</p>
                  <p className="text-sm text-ink">{result.recommendation}</p>
                </div>

                {/* Drifted features */}
                {result.drifted_features.length > 0 && (
                  <div className="bg-surface border border-border rounded-lg px-5 py-4">
                    <p className="font-mono text-xs text-ink-faint mb-3">Drifted Features</p>
                    <div className="flex flex-wrap gap-2">
                      {result.drifted_features.map(f => (
                        <span
                          key={f}
                          className="font-mono text-xs bg-canvas border border-border rounded px-2 py-1"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {!result && !loading && !error && (
          <div className="bg-surface border border-border rounded-lg p-12 text-center">
            <p className="text-ink-muted font-mono text-sm">
              Select a model and click "Run Comparison" to start.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
