import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import type { DriftRun, FeatureResult, AgentLogEntry } from "../types"
import { driftApi } from "../api/client"
import { agentApi } from "../api/agent-client"
import { RegimeBadge } from "../components/RegimeBadge"
import { SeverityBar } from "../components/SeverityBar"
import { ActionCard } from "../components/ActionCard"
import { ImpactBanner } from "../components/ImpactBanner"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"

export function ModelDetail() {
  const { modelId } = useParams<{ modelId: string }>()
  const navigate = useNavigate()
  const [history, setHistory]     = useState<DriftRun[]>([])
  const [features, setFeatures]   = useState<FeatureResult[]>([])
  const [agentLog, setAgentLog]   = useState<AgentLogEntry | null>(null)
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    if (!modelId) return
    driftApi.history(modelId).then(h => {
      setHistory(h)
      if (h.length > 0) {
        driftApi.features(modelId, h[0].id).then(f => {
          const psi = f.filter((r: FeatureResult) => r.detector === "psi")
          setFeatures(psi)
        })
      }
    }).finally(() => setLoading(false))

    // Fetch latest agent decision (best-effort — never blocks the page)
    agentApi.log(modelId, 1).then(entries => {
      if (entries.length > 0) setAgentLog(entries[0])
    }).catch(() => {})
  }, [modelId])

  const latest = history[0]
  const chartData = [...history].reverse().map(r => ({
    date: new Date(r.checked_at).toLocaleDateString(),
    score: r.drift_score,
    severity: r.overall_severity,
  }))

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-surface border-b border-border px-8 py-4 flex items-center gap-4 sticky top-0 z-10">
        <button
          onClick={() => navigate("/")}
          className="text-ink-faint hover:text-ink font-mono text-sm transition-colors"
        >
          ← back
        </button>
        <div className="w-px h-4 bg-border" />
        <span className="font-display font-semibold text-ink">{modelId}</span>
        {latest && <RegimeBadge regime={latest.regime} />}
      </header>

      <main className="max-w-5xl mx-auto px-8 py-8">
        {loading ? (
          <div className="h-48 bg-surface border border-border rounded-lg animate-pulse" />
        ) : history.length === 0 ? (
          <div className="bg-surface border border-border rounded-lg p-12 text-center">
            <p className="text-ink-muted font-mono text-sm">No drift runs for this model yet.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Agent action card — shown when a prior governance decision exists */}
            {agentLog && (
              <ActionCard
                action={agentLog.action}
                confidence={agentLog.confidence}
                regime={agentLog.regime_context as any || latest.regime}
                recommendation=""
                topFeatures={features.slice(0, 3).map(f => f.feature_name)}
              />
            )}

            {/* Business impact banner — shown when drift is material */}
            {latest.drift_score > 0.10 && (
              <ImpactBanner
                psiScore={latest.drift_score}
                regime={latest.regime}
              />
            )}

            {/* Summary row */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Drift score", value: latest.drift_score.toFixed(4) },
                { label: "Severity",    value: latest.overall_severity.toUpperCase() },
                { label: "Regime",      value: latest.regime ?? "unknown" },
              ].map(s => (
                <div key={s.label} className="bg-surface border border-border rounded-lg p-4">
                  <p className="text-ink-faint text-xs mb-1">{s.label}</p>
                  <p className="font-mono font-medium text-ink text-lg">{s.value}</p>
                </div>
              ))}
            </div>

            {/* Recommendation from drift run notes */}
            {latest.notes && (
              <div className="bg-accent-soft border border-accent/20 rounded-lg px-5 py-4">
                <p className="text-xs font-mono text-accent font-medium mb-1">Recommendation</p>
                <p className="text-sm text-ink">{latest.notes}</p>
              </div>
            )}

            {/* Drift history chart */}
            <div className="bg-surface border border-border rounded-lg p-5">
              <h2 className="font-display font-medium text-sm text-ink mb-4">Drift score history</h2>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={chartData}>
                  <XAxis dataKey="date" tick={{ fontSize: 10, fontFamily: "DM Mono" }} />
                  <YAxis tick={{ fontSize: 10, fontFamily: "DM Mono" }} domain={[0, "auto"]} />
                  <Tooltip
                    contentStyle={{ fontFamily: "DM Mono", fontSize: 11, border: "1px solid #E8E6E0" }}
                  />
                  <ReferenceLine y={0.25} stroke="#D4450C" strokeDasharray="3 3" strokeWidth={1} />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#D4450C"
                    strokeWidth={1.5}
                    dot={{ r: 3, fill: "#D4450C" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Feature drift table */}
            {features.length > 0 && (
              <div className="bg-surface border border-border rounded-lg">
                <div className="px-5 py-4 border-b border-border-subtle">
                  <h2 className="font-display font-medium text-sm text-ink">Feature drift — PSI</h2>
                </div>
                <div className="divide-y divide-border-subtle">
                  {features
                    .sort((a, b) => b.score - a.score)
                    .map(f => (
                      <div key={f.feature_name} className="px-5 py-3 grid grid-cols-3 gap-4 items-center">
                        <span className="font-mono text-xs text-ink">{f.feature_name}</span>
                        <SeverityBar severity={f.severity} score={f.score} />
                        <span className="font-mono text-xs text-ink-faint text-right">{f.severity}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}