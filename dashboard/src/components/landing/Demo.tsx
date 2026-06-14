import { useEffect, useRef, useState } from "react"
import { DEMO } from "../../lib/constants"

type Scenario = typeof DEMO.scenarios[0]

const TAG_COLORS: Record<string, { bg: string; color: string; accent: string }> = {
  amber: { bg: "#FAEEDA", color: "#854F0B", accent: "#854F0B" },
  red:   { bg: "#FCEBEB", color: "#A32D2D", accent: "#A32D2D" },
  teal:  { bg: "#E1F5EE", color: "#0F6E56", accent: "#0F6E56" },
}

function colorLine(line: string): React.ReactNode {
  if (line.includes("HALT")) return <span style={{ color: "#FF6B6B", fontWeight: 600 }}>{line}</span>
  if (line.startsWith("$"))   return <span style={{ color: "#6C7A8D" }}>{line}</span>

  const parts: React.ReactNode[] = []
  const tokens = line.split(/(\w+:)/)
  tokens.forEach((tok, i) => {
    if (tok === "drift:" || tok === "severity:")
      parts.push(<span key={i} style={{ color: "#F5A623" }}>{tok}</span>)
    else if (tok === "regime:")
      parts.push(<span key={i} style={{ color: "#4ADE80" }}>{tok}</span>)
    else if (tok === "action:" || tok === "confidence:")
      parts.push(<span key={i} style={{ color: "#34D399" }}>{tok}</span>)
    else
      parts.push(<span key={i} style={{ color: "#E2E8F0" }}>{tok}</span>)
  })
  return <>{parts}</>
}

export function Demo() {
  const [selected, setSelected] = useState<Scenario | null>(null)
  const [lines, setLines]     = useState<string[]>([])
  const [typing, setTyping]   = useState(false)
  const prefersReduced = typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([])

  function runScenario(scenario: Scenario) {
    timerRef.current.forEach(clearTimeout)
    timerRef.current = []
    setSelected(scenario)
    setLines([])
    setTyping(true)

    if (prefersReduced) { setLines(scenario.output); setTyping(false); return }

    scenario.output.forEach((line, i) => {
      const t = setTimeout(() => {
        setLines(prev => [...prev, line])
        if (i === scenario.output.length - 1) setTyping(false)
      }, i * 120)
      timerRef.current.push(t)
    })
  }

  useEffect(() => () => timerRef.current.forEach(clearTimeout), [])

  return (
    <section aria-label="Demo" style={{ background: "#F8F8F7" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "4.5rem 2rem" }}>

        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "0.75rem" }}>
          <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9" }}>04</span>
          <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9" }}>See it run</span>
        </div>

        <h2 style={{
          fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)", fontWeight: 600,
          letterSpacing: "-0.03em", marginBottom: "2rem", lineHeight: 1.25, color: "#2C2C2A",
          whiteSpace: "pre-line",
        }}>
          {DEMO.heading}
        </h2>

        {/* Scenario selector strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", marginBottom: "1rem" }}
          className="demo-grid">
          {DEMO.scenarios.map(s => {
            const tc = TAG_COLORS[s.tagColor]
            const isSel = selected?.id === s.id
            return (
              <div
                key={s.id}
                role="button" tabIndex={0} aria-pressed={isSel}
                onClick={() => runScenario(s)}
                onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); runScenario(s) } }}
                style={{
                  background: isSel ? "#fff" : "#fff",
                  border: isSel ? `1.5px solid #2D8C5A` : "1px solid rgba(0,0,0,0.08)",
                  borderRadius: 10, padding: "1.25rem",
                  cursor: "pointer",
                  boxShadow: isSel ? "0 0 0 3px rgba(60,52,137,0.1)" : "none",
                  transition: "border-color 0.15s, box-shadow 0.15s",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span style={{
                    background: tc.bg, color: tc.color,
                    borderRadius: 6, fontSize: "0.6875rem",
                    fontFamily: "'Geist Mono', monospace", padding: "3px 8px", fontWeight: 600,
                  }}>{s.tag}</span>
                  {isSel && <span style={{ color: "#2D8C5A", fontSize: "0.75rem", fontWeight: 600 }}>● active</span>}
                </div>
                <p style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#2C2C2A", marginBottom: 4 }}>{s.title}</p>
                <p style={{ fontSize: "0.8rem", color: "#5F5E5A", fontFamily: "'Geist Mono', monospace" }}>{s.meta}</p>
                {!isSel && (
                  <button
                    onClick={e => { e.stopPropagation(); runScenario(s) }}
                    style={{
                      marginTop: "0.75rem", fontSize: "0.8125rem", color: "#2D8C5A",
                      fontWeight: 600, background: "none", border: "none", padding: 0, cursor: "pointer",
                    }}
                  >Run →</button>
                )}
              </div>
            )
          })}
        </div>

        {/* Terminal */}
        <div
          role="log" aria-live="polite" aria-label="Demo terminal output"
          style={{
            background: "#13131F", borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.06)",
            overflow: "hidden",
          }}
        >
          {/* Title bar */}
          <div style={{
            background: "#1E1E2E", padding: "0.75rem 1.25rem",
            display: "flex", alignItems: "center", gap: "0.5rem",
            borderBottom: "1px solid rgba(255,255,255,0.05)",
          }}>
            <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#FF5F57", display: "inline-block" }} />
            <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#FFBD2E", display: "inline-block" }} />
            <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#28C840", display: "inline-block" }} />
            <span style={{ marginLeft: 12, color: "#6C7A8D", fontSize: "0.75rem", fontFamily: "'Geist Mono', monospace" }}>
              driftguard — demo
            </span>
          </div>
          {/* Output */}
          <div style={{
            padding: "1.25rem 1.5rem", minHeight: 140,
            fontFamily: "'Geist Mono', monospace", fontSize: "0.8125rem", lineHeight: 2,
          }}>
            {lines.length === 0 && !typing
              ? <span style={{ color: "#3C4557" }}>$ select a scenario above to run</span>
              : lines.map((line, i) => <div key={i}>{colorLine(line)}</div>)
            }
            {typing && <span style={{ color: "#6C7A8D", animation: "blink 1s step-start infinite" }}>▌</span>}
          </div>
        </div>

      </div>

      <style>{`
        @media (max-width: 639px) { .demo-grid { grid-template-columns: 1fr !important; } }
        @keyframes blink { 0%, 100% { opacity: 1 } 50% { opacity: 0 } }
      `}</style>
    </section>
  )
}
