import { useEffect, useState } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import type { DriftRun, FeatureResult, AgentLogEntry, ModelVersion } from "../types"
import { driftApi, versionsApi } from "../api/client"
import { agentApi } from "../api/agent-client"
import { RegimeBadge } from "../components/RegimeBadge"
import { SeverityBar } from "../components/SeverityBar"
import { ActionCard } from "../components/ActionCard"
import { ImpactBanner } from "../components/ImpactBanner"
import { DriftChart } from "../components/DriftChart"
import { HaltOverlay } from "../components/HaltOverlay"
import { DemoPanel } from "../components/DemoPanel"

function VersionBadge({ version }: { version: ModelVersion }) {
  const base =
    "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono border"
  if (version.is_active) {
    return (
      <span className={`${base} border-accent/40 bg-accent-soft text-accent`}>
        {version.version_label} <span className="opacity-60">(active)</span>
      </span>
    )
  }
  return (
    <span className={`${base} border-border text-ink-faint`}>
      {version.version_label}
    </span>
  )
}

export function ModelDetail() {
  const { modelId } = useParams<{ modelId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const demoMode = searchParams.get("demo") === "true"

  const [history, setHistory]         = useState<DriftRun[]>([])
  const [features, setFeatures]       = useState<FeatureResult[]>([])
  const [agentLog, setAgentLog]       = useState<AgentLogEntry | null>(null)
  const [loading, setLoading]         = useState(true)
  const [versions, setVersions]       = useState<ModelVersion[]>([])
  const [selectedVersion, setSelectedVersion] = useState<string>("")

  const loadHistory = (version?: string) => {
    if (!modelId) return
    driftApi.history(modelId, version || undefined).then(h => {
      setHistory(h)
      if (h.length > 0) {
        driftApi.features(modelId, h[0].id).then(f => {
          const psi = f.filter((r: FeatureResult) => r.detector === "psi")
          setFeatures(psi)
        })
      } else {
        setFeatures([])
      }
    })
  }

  const refreshHistory = () => loadHistory(selectedVersion || undefined)

  useEffect(() => {
    if (!modelId) return

    versionsApi.list(modelId).then(vs => {
      setVersions(vs)
      // default to active version if any
      const active = vs.find(v => v.is_active)
      if (active) setSelectedVersion(active.version_label)
    }).catch(() => {})

    driftApi.history(modelId).then(h => {
      setHistory(h)
      if (h.length > 0) {
        driftApi.features(modelId, h[0].id).then(f => {
          const psi = f.filter((r: FeatureResult) => r.detector === "psi")
          setFeatures(psi)
        })
      }
    }).finally(() => setLoading(false))

    agentApi.log(modelId, 1).then(entries => {
      if (entries.length > 0) setAgentLog(entries[0])
    }).catch(() => {})
  }, [modelId])

  // Reload history when version selection changes (after initial load)
  const handleVersionChange = (label: string) => {
    setSelectedVersion(label)
    loadHistory(label || undefined)
  }

  const latest = history[0]
  const activeVersion = versions.find(v => v.is_active)

  return (
    <div className="min-h-screen bg-canvas">
      {latest && (
        <HaltOverlay runId={latest.id} regime={latest.regime} />
      )}
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
        {/* Version badges */}
        {versions.length > 0 && (
          <div className="flex items-center gap-2 ml-2">
            {versions.map(v => (
              <VersionBadge key={v.id} version={v} />
            ))}
          </div>
        )}
      </header>

      <main className="max-w-5xl mx-auto px-8 py-8">
        {loading ? (
          <div className="h-48 bg-surface border border-border rounded-lg animate-pulse" />
        ) : history.length === 0 && !selectedVersion ? (
          <div className="bg-surface border border-border rounded-lg p-12 text-center">
            <p className="text-ink-muted font-mono text-sm">No drift runs for this model yet.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Version selector */}
            {versions.length > 1 && (
              <div className="bg-surface border border-border rounded-lg px-5 py-3 flex items-center gap-3">
                <span className="text-xs font-mono text-ink-faint">Version</span>
                <select
                  value={selectedVersion}
                  onChange={e => handleVersionChange(e.target.value)}
                  className="bg-canvas border border-border rounded px-2 py-1 text-xs font-mono text-ink focus:outline-none focus:border-accent"
                >
                  <option value="">All versions</option>
                  {versions.map(v => (
                    <option key={v.id} value={v.version_label}>
                      {v.version_label}{v.is_active ? " (active)" : ""}
                      {v.description ? ` — ${v.description}` : ""}
                    </option>
                  ))}
                </select>
                {activeVersion && (
                  <span className="text-xs font-mono text-ink-faint">
                    Champion: <span className="text-accent">{activeVersion.version_label}</span>
                    {activeVersion.promoted_at && (
                      <span className="opacity-60"> since {new Date(activeVersion.promoted_at).toLocaleDateString()}</span>
                    )}
                  </span>
                )}
              </div>
            )}

            {history.length === 0 ? (
              <div className="bg-surface border border-border rounded-lg p-12 text-center">
                <p className="text-ink-muted font-mono text-sm">
                  No drift runs for version <span className="text-accent">{selectedVersion}</span>.
                </p>
              </div>
            ) : (
              <>
                {/* Demo control panel — shown only when ?demo=true */}
                {demoMode && modelId && (
                  <DemoPanel modelId={modelId} onRefresh={refreshHistory} />
                )}

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
                  <h2 className="font-display font-medium text-sm text-ink mb-4">
                    Drift score history
                    {selectedVersion && (
                      <span className="ml-2 text-xs font-mono text-ink-faint">
                        ({selectedVersion})
                      </span>
                    )}
                  </h2>
                  <DriftChart history={history} />
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
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
