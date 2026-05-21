import { useEffect, useState } from "react"
import type { Model, Alert } from "../types"
import { modelsApi, alertsApi } from "../api/client"
import { ModelHealthCard } from "../components/ModelHealthCard"
import { AlertFeed } from "../components/AlertFeed"
import { MacroPanel } from "../components/MacroPanel"
import { ForecastAlert } from "../components/ForecastAlert"
import { useNavigate } from "react-router-dom"

type Persona = "engineer" | "quant" | "risk"

const PERSONA_CONFIG: Record<Persona, { label: string; cta: string; ctaPath: string; description: string }> = {
  engineer: {
    label:       "Engineer",
    cta:         "Model detail",
    ctaPath:     "/models",
    description: "Drift scores, feature breakdown, and regime context",
  },
  quant: {
    label:       "Quant / DS",
    cta:         "Champion-Challenger",
    ctaPath:     "/experiments",
    description: "Experiment comparison and model version analysis",
  },
  risk: {
    label:       "Risk Officer",
    cta:         "Governance Agent",
    ctaPath:     "/agent",
    description: "Plain-language compliance chat and PDF report generation",
  },
}

export function Overview() {
  const [models, setModels]     = useState<Model[]>([])
  const [alerts, setAlerts]     = useState<Alert[]>([])
  const [loading, setLoading]   = useState(true)
  const [persona, setPersona]   = useState<Persona>("engineer")
  const navigate = useNavigate()

  const fetchAlerts = () =>
    alertsApi.list(true).then(setAlerts).catch(() => setAlerts([]))

  useEffect(() => {
    Promise.all([modelsApi.list(), alertsApi.list(true)])
      .then(([m, a]) => { setModels(m); setAlerts(a) })
      .finally(() => setLoading(false))
  }, [])

  const pc = PERSONA_CONFIG[persona]

  return (
    <div className="min-h-screen bg-canvas">
      {/* ── Header ── */}
      <header className="bg-surface border-b border-border px-8 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-accent pulse-dot" />
          <span className="font-display font-semibold text-ink tracking-tight">DriftGuard</span>
          <span className="text-ink-faint font-mono text-xs">v0.1.0</span>
        </div>

        <nav className="flex items-center gap-4">
          <button
            onClick={() => navigate("/experiments")}
            className="text-ink-faint hover:text-ink font-mono text-xs transition-colors"
          >
            experiments
          </button>
          <button
            onClick={() => navigate("/agent")}
            className="text-ink-faint hover:text-ink font-mono text-xs transition-colors"
          >
            agent
          </button>
          <div className="w-px h-3 bg-border" />
          <button
            onClick={() => navigate("/settings")}
            className="text-ink-faint hover:text-ink font-mono text-xs transition-colors"
          >
            settings
          </button>
          {alerts.length > 0 && (
            <span className="bg-critical-soft text-critical font-mono text-xs px-2.5 py-1 rounded-full border border-critical/20">
              {alerts.length} unacknowledged
            </span>
          )}
          <span className="text-ink-faint font-mono text-xs hidden sm:block">
            {new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
          </span>
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-8">
        {/* ── Title + persona selector ── */}
        <div className="flex items-start justify-between gap-6 mb-8 flex-wrap">
          <div>
            <h1 className="font-display font-semibold text-2xl text-ink tracking-tight">
              Model health
            </h1>
            <p className="text-ink-muted text-sm mt-1">
              Drift monitoring with financial regime awareness
            </p>
          </div>

          {/* "I am a…" persona toggle */}
          <div className="flex flex-col items-end gap-2">
            <span className="font-mono text-xs text-ink-faint">I am a…</span>
            <div className="flex gap-1 bg-border-subtle rounded-lg p-0.5">
              {(Object.keys(PERSONA_CONFIG) as Persona[]).map(p => (
                <button
                  key={p}
                  onClick={() => setPersona(p)}
                  className={[
                    "px-3 py-1.5 rounded-md font-mono text-xs transition-colors",
                    persona === p
                      ? "bg-surface text-ink shadow-sm"
                      : "text-ink-faint hover:text-ink",
                  ].join(" ")}
                >
                  {PERSONA_CONFIG[p].label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Persona CTA banner ── */}
        <div className="mb-6 bg-surface border border-border rounded-lg px-5 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-ink-faint mb-0.5">{PERSONA_CONFIG[persona].label} view</p>
            <p className="text-sm text-ink">{pc.description}</p>
          </div>
          <button
            onClick={() => navigate(pc.ctaPath === "/models" && models.length > 0
              ? `/models/${models[0].model_id}`
              : pc.ctaPath
            )}
            className="shrink-0 px-4 py-2 bg-accent text-white text-xs font-mono rounded-md hover:bg-accent/90 transition-colors"
          >
            {pc.cta} →
          </button>
        </div>

        {/* ── Macro panel ── */}
        <div className="mb-6">
          <MacroPanel />
        </div>

        {/* ── Proactive forecast banner ── */}
        {models.length > 0 && (
          <ForecastAlert modelId={models[0].model_id} />
        )}

        {/* ── Model cards ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-surface border border-border rounded-lg animate-pulse" />
            ))}
          </div>
        ) : models.length === 0 ? (
          <div className="bg-surface border border-border rounded-lg p-12 text-center">
            <p className="text-ink-muted font-mono text-sm">No models registered yet.</p>
            <p className="text-ink-faint font-mono text-xs mt-1">POST /models/ to register your first model.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
            {models.map(model => (
              <ModelHealthCard
                key={model.model_id}
                model={model}
                onClick={() => navigate(`/models/${model.model_id}`)}
              />
            ))}
          </div>
        )}

        {/* ── Alert feed ── */}
        <div className="bg-surface border border-border rounded-lg">
          <div className="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
            <h2 className="font-display font-medium text-sm text-ink">Recent alerts</h2>
            <span className="font-mono text-xs text-ink-faint">unacknowledged only</span>
          </div>
          <div className="px-5 py-2">
            <AlertFeed alerts={alerts} onAck={fetchAlerts} />
          </div>
        </div>
      </main>
    </div>
  )
}