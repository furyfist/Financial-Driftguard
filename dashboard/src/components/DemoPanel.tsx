import { useRef, useState } from "react"
import axios from "axios"
import type { Regime } from "../types"
import { RegimeBadge } from "./RegimeBadge"

const api = axios.create({ baseURL: "http://localhost:8000" })

interface ScenarioConfig {
  name: string
  title: string
  regime: Regime
  expectedOutcome: string
  borderColor: string
}

const SCENARIOS: ScenarioConfig[] = [
  {
    name: "rate_hike_q4_2018",
    title: "Rate Hike Q4 2018",
    regime: "credit_stress",
    expectedOutcome: "Expected: monitor, don't retrain",
    borderColor: "#B45309",
  },
  {
    name: "covid_crash_march_2020",
    title: "COVID Crash March 2020",
    regime: "black_swan",
    expectedOutcome: "Expected: HALT",
    borderColor: "#C0200F",
  },
  {
    name: "normal_model_decay",
    title: "Normal Model Decay",
    regime: "stable",
    expectedOutcome: "Expected: investigate, retrain",
    borderColor: "#1A6B3C",
  },
]

interface LogEntry {
  scenario: string
  regime: string | null
  drift_score: number
  notes: string
  timestamp: string
}

interface Props {
  modelId: string
  onRefresh: () => void
}

export function DemoPanel({ modelId, onRefresh }: Props) {
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [log, setLog] = useState<LogEntry[]>([])
  const logRef = useRef<HTMLDivElement>(null)

  const runScenario = async (scenarioName: string) => {
    setLoading(prev => ({ ...prev, [scenarioName]: true }))
    try {
      const resp = await api.post(`/demo/scenarios/${scenarioName}?model_id=${encodeURIComponent(modelId)}`)
      const data = resp.data
      const entry: LogEntry = {
        scenario: scenarioName,
        regime: data.regime,
        drift_score: data.drift_score,
        notes: data.notes ?? "",
        timestamp: new Date().toLocaleTimeString(),
      }
      setLog(prev => {
        const next = [...prev, entry]
        // scroll after state update
        setTimeout(() => {
          if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
        }, 0)
        return next
      })
      onRefresh()
    } catch {
      const entry: LogEntry = {
        scenario: scenarioName,
        regime: null,
        drift_score: 0,
        notes: "Error: scenario failed — check backend",
        timestamp: new Date().toLocaleTimeString(),
      }
      setLog(prev => [...prev, entry])
    } finally {
      setLoading(prev => ({ ...prev, [scenarioName]: false }))
    }
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="font-display font-medium text-sm text-ink">Demo Scenarios</span>
        <span className="font-mono text-xs px-2 py-0.5 rounded-full border bg-warning-soft text-warning border-warning/20">
          demo mode
        </span>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Scenario cards */}
        <div className="flex flex-col sm:flex-row gap-3 flex-1">
          {SCENARIOS.map(s => (
            <div
              key={s.name}
              className="flex-1 bg-canvas border border-border rounded-lg p-4 space-y-3"
              style={{ borderLeftColor: s.borderColor, borderLeftWidth: "4px" }}
            >
              <div className="space-y-1.5">
                <p className="font-display font-semibold text-sm text-ink leading-tight">{s.title}</p>
                <RegimeBadge regime={s.regime} />
              </div>
              <p className="font-mono text-xs text-ink-faint">{s.expectedOutcome}</p>
              <button
                onClick={() => runScenario(s.name)}
                disabled={loading[s.name]}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-surface border border-border rounded-md font-mono text-xs text-ink-muted hover:text-ink hover:border-accent/40 disabled:opacity-50 transition-colors"
              >
                {loading[s.name] ? (
                  <>
                    <span className="w-3 h-3 border border-ink-faint border-t-ink rounded-full animate-spin" />
                    Running…
                  </>
                ) : (
                  "Run Scenario"
                )}
              </button>
            </div>
          ))}
        </div>

        {/* Live log panel */}
        <div className="w-full lg:w-72 bg-[#0d0d0d] rounded-lg p-3">
          <p className="font-mono text-xs text-[#555] mb-2">// live output</p>
          <div
            ref={logRef}
            className="overflow-y-auto space-y-3"
            style={{ maxHeight: "200px" }}
          >
            {log.length === 0 ? (
              <p className="font-mono text-xs text-[#444]">Run a scenario to see output…</p>
            ) : (
              log.map((entry, i) => (
                <div key={i} className="space-y-0.5">
                  <p className="font-mono text-[10px] text-[#666]">[{entry.timestamp}] {entry.scenario}</p>
                  <p className="font-mono text-xs text-[#4ade80]">regime: {entry.regime ?? "unknown"}</p>
                  <p className="font-mono text-xs text-[#60a5fa]">drift:  {entry.drift_score.toFixed(4)}</p>
                  <p className="font-mono text-[10px] text-[#f9a8d4] leading-tight">{entry.notes.slice(0, 90)}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
