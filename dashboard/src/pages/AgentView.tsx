import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import type { Action, Regime, Model } from "../types"
import { modelsApi } from "../api/client"
import { agentApi, reportApi } from "../api/agent-client"
import { RegimeBadge } from "../components/RegimeBadge"
import { AgentResponseCard } from "../components/AgentResponseCard"

// ── Types ──────────────────────────────────────────────────────────────────────

interface AgentMessage {
  role:        "user" | "agent"
  text:        string
  action?:     Action
  regime?:     Regime | null
  confidence?: number
  reasoning?:  string
  sources?:    string[]
  timestamp:   Date
}

// ── Action badge (inline, smaller than ActionCard) ────────────────────────────

const ACTION_COLOR: Record<string, string> = {
  monitor:              "bg-stable-soft text-stable border-stable/20",
  proceed:              "bg-stable-soft text-stable border-stable/20",
  investigate:          "bg-warning-soft text-warning border-warning/20",
  proceed_with_caution: "bg-warning-soft text-warning border-warning/20",
  champion_challenger:  "bg-warning-soft text-warning border-warning/20",
  retrain:              "bg-warning-soft text-warning border-warning/20",
  freeze:               "bg-critical-soft text-critical border-critical/20",
  escalate:             "bg-critical-soft text-critical border-critical/20",
  halt:                 "bg-critical-soft text-critical border-critical/20",
}

const ACTION_LABEL: Record<string, string> = {
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

function InlineActionBadge({ action }: { action: Action }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border font-mono text-xs font-semibold ${ACTION_COLOR[action] ?? "bg-border-subtle text-ink-muted border-border"}`}>
      {ACTION_LABEL[action] ?? action}
    </span>
  )
}

// ── Message bubbles ────────────────────────────────────────────────────────────

function UserBubble({ msg }: { msg: AgentMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[72%]">
        <p className="bg-accent text-white text-sm rounded-2xl rounded-tr-sm px-4 py-3 leading-relaxed">
          {msg.text}
        </p>
        <p className="text-ink-faint font-mono text-xs mt-1 text-right">
          {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  )
}

function AgentBubble({ msg }: { msg: AgentMessage }) {
  const [showReasoning, setShowReasoning] = useState(false)
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] space-y-2">
        {/* Header row */}
        <div className="flex items-center gap-2 flex-wrap pl-1">
          <span className="font-mono text-xs text-ink-faint">FinSight AI</span>
          {msg.action && <InlineActionBadge action={msg.action} />}
          {msg.regime && <RegimeBadge regime={msg.regime} />}
          {msg.confidence !== undefined && (
            <span className="font-mono text-xs text-ink-faint">
              {Math.round(msg.confidence * 100)}% confidence
            </span>
          )}
        </div>

        {/* Message body */}
        <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-3">
          <p className="text-sm text-ink leading-relaxed">{msg.text}</p>

          {/* Reasoning toggle */}
          {msg.reasoning && (
            <div className="mt-3 pt-3 border-t border-border-subtle">
              <button
                onClick={() => setShowReasoning(v => !v)}
                className="font-mono text-xs text-ink-faint hover:text-ink transition-colors"
              >
                {showReasoning ? "Hide reasoning" : "Show reasoning"}
              </button>
              {showReasoning && (
                <p className="mt-2 text-xs text-ink-muted leading-relaxed">{msg.reasoning}</p>
              )}
            </div>
          )}
        </div>

        <p className="text-ink-faint font-mono text-xs pl-1">
          {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  )
}

// ── Suggestion chips ────────────────────────────────────────────────────────────

const SUGGESTION_CHIPS = [
  "Is my lending model safe right now?",
  "What happened in March 2020?",
  "Should I retrain?",
  "Why did int_rate drift?",
]

// ── Main page ──────────────────────────────────────────────────────────────────

export function AgentView() {
  const navigate = useNavigate()

  const [models, setModels]           = useState<Model[]>([])
  const [modelId, setModelId]         = useState<string>("")
  const [messages, setMessages]       = useState<AgentMessage[]>([])
  const [input, setInput]             = useState("")
  const [thinking, setThinking]       = useState(false)
  const [reportLoading, setReportLoad]= useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [sendError, setSendError]     = useState<string | null>(null)

  const bottomRef  = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    modelsApi.list().then(ms => {
      setModels(ms)
      if (ms.length > 0) setModelId(ms[0].model_id)
    }).catch(() => {})
  }, [])

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, thinking])

  const send = async (text: string) => {
    const query = text.trim()
    if (!query || thinking) return

    setSendError(null)
    setInput("")

    const userMsg: AgentMessage = { role: "user", text: query, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setThinking(true)

    try {
      const resp = await agentApi.ask(query, modelId || undefined)
      const agentMsg: AgentMessage = {
        role:       "agent",
        text:       resp.recommendation,
        action:     resp.action,
        regime:     null,
        confidence: resp.confidence,
        reasoning:  resp.reasoning,
        sources:    resp.sources,
        timestamp:  new Date(),
      }
      setMessages(prev => [...prev, agentMsg])
    } catch (err: any) {
      setSendError(err?.response?.data?.detail ?? "Agent is unavailable. Check the backend is running.")
    } finally {
      setThinking(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  const handleReport = async () => {
    if (!modelId) return
    setReportError(null)
    setReportLoad(true)
    try {
      await reportApi.download(modelId)
    } catch (err: any) {
      setReportError(err.message ?? "Report generation failed.")
    } finally {
      setReportLoad(false)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="min-h-screen bg-canvas flex flex-col">

      {/* ── Header ── */}
      <header className="bg-surface border-b border-border px-8 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="text-ink-faint hover:text-ink font-mono text-xs transition-colors"
          >
            ← overview
          </button>
          <span className="text-ink-faint font-mono text-xs">/</span>
          <span className="font-display font-semibold text-ink tracking-tight">Governance Agent</span>
          <span className="font-mono text-xs px-2 py-0.5 rounded-full border bg-stable-soft text-stable border-stable/20">
            Risk Officer View
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Model selector */}
          {models.length > 0 && (
            <select
              value={modelId}
              onChange={e => setModelId(e.target.value)}
              className="bg-canvas border border-border rounded-md px-2.5 py-1.5 text-xs text-ink font-mono focus:outline-none focus:ring-1 focus:ring-accent"
            >
              {models.map(m => (
                <option key={m.model_id} value={m.model_id}>{m.model_id}</option>
              ))}
            </select>
          )}

          {/* Report button */}
          <button
            onClick={handleReport}
            disabled={!modelId || reportLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-surface border border-border rounded-md font-mono text-xs text-ink-muted hover:text-ink hover:border-accent/40 disabled:opacity-50 transition-colors"
          >
            {reportLoading ? (
              <span className="inline-block w-3 h-3 border border-ink-faint border-t-ink rounded-full animate-spin" />
            ) : (
              <span>↓</span>
            )}
            {reportLoading ? "Generating…" : "Compliance Report"}
          </button>
        </div>
      </header>

      {/* ── Report error ── */}
      {reportError && (
        <div className="mx-8 mt-4 px-4 py-2.5 bg-critical-soft border border-critical/20 rounded-lg text-critical text-xs font-mono">
          {reportError}
        </div>
      )}

      {/* ── Chat area ── */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8 flex flex-col">

        {/* Empty state */}
        {isEmpty && (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-8 pb-16">
            <div>
              <div className="w-12 h-12 rounded-full bg-stable-soft border border-stable/20 flex items-center justify-center mx-auto mb-4">
                <span className="text-stable text-xl">◎</span>
              </div>
              <h2 className="font-display font-semibold text-xl text-ink">FinSight AI</h2>
              <p className="text-ink-muted text-sm mt-1 max-w-sm">
                Ask about model health, drift causes, or compliance risk — in plain language.
              </p>
            </div>

            {/* Suggestion chips */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
              {SUGGESTION_CHIPS.map(chip => (
                <button
                  key={chip}
                  onClick={() => send(chip)}
                  disabled={thinking}
                  className="text-left px-4 py-3 bg-surface border border-border rounded-xl text-sm text-ink-muted hover:text-ink hover:border-accent/30 transition-colors font-body leading-snug"
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {!isEmpty && (
          <div className="flex-1 space-y-6 pb-4">
            {messages.map((msg, i) =>
              msg.role === "user"
                ? <UserBubble key={i} msg={msg} />
                : <AgentBubble key={i} msg={msg} />
            )}

            {/* Thinking indicator */}
            {thinking && (
              <div className="flex justify-start">
                <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1 items-center h-4">
                    {[0, 1, 2].map(i => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-ink-faint animate-bounce"
                        style={{ animationDelay: `${i * 150}ms` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Send error */}
            {sendError && (
              <div className="px-4 py-2.5 bg-critical-soft border border-critical/20 rounded-lg text-critical text-xs font-mono">
                {sendError}
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </main>

      {/* ── Input bar ── */}
      <div className="sticky bottom-0 bg-canvas border-t border-border px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about model health, compliance risk, or drift causes…"
            rows={1}
            disabled={thinking}
            className="flex-1 resize-none bg-surface border border-border rounded-xl px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60 font-body leading-relaxed"
            style={{ minHeight: "48px", maxHeight: "160px" }}
            onInput={e => {
              const t = e.currentTarget
              t.style.height = "auto"
              t.style.height = `${t.scrollHeight}px`
            }}
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || thinking}
            className="shrink-0 w-11 h-11 rounded-xl bg-accent text-white flex items-center justify-center hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Send"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M14 8L2 2l2 6-2 6 12-6z" fill="currentColor" />
            </svg>
          </button>
        </div>
        <p className="text-center font-mono text-xs text-ink-faint mt-2">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
