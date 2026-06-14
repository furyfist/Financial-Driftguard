import { useEffect, useRef, useState } from "react"
import { DEMO } from "../../lib/constants"

type Scenario = typeof DEMO.scenarios[0]

const TAG_COLORS: Record<string, { bg: string; color: string }> = {
  amber: { bg: "#FAEEDA", color: "#854F0B" },
  red:   { bg: "#FCEBEB", color: "#A32D2D" },
  teal:  { bg: "#E1F5EE", color: "#0F6E56" },
}

function colorLine(line: string): React.ReactNode {
  if (line.includes("HALT")) {
    return <span style={{ color: "#A32D2D" }}>{line}</span>
  }
  if (line.startsWith("$")) {
    return <span style={{ color: "#B4B2A9" }}>{line}</span>
  }
  const parts: React.ReactNode[] = []
  const tokens = line.split(/(\w+:)/)
  tokens.forEach((tok, i) => {
    if (tok === "drift:" || tok === "severity:") {
      parts.push(<span key={i} style={{ color: "#854F0B" }}>{tok}</span>)
    } else if (tok === "regime:") {
      parts.push(<span key={i} style={{ color: "#3C3489" }}>{tok}</span>)
    } else if (tok === "action:" || tok === "confidence:") {
      parts.push(<span key={i} style={{ color: "#0F6E56" }}>{tok}</span>)
    } else {
      parts.push(<span key={i}>{tok}</span>)
    }
  })
  return <>{parts}</>
}

export function Demo() {
  const [selected, setSelected] = useState<Scenario | null>(null)
  const [lines, setLines] = useState<string[]>([])
  const [typing, setTyping] = useState(false)
  const prefersReduced = typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([])

  function runScenario(scenario: Scenario) {
    timerRef.current.forEach(clearTimeout)
    timerRef.current = []
    setSelected(scenario)
    setLines([])
    setTyping(true)

    if (prefersReduced) {
      setLines(scenario.output)
      setTyping(false)
      return
    }

    scenario.output.forEach((line, i) => {
      const t = setTimeout(() => {
        setLines(prev => [...prev, line])
        if (i === scenario.output.length - 1) setTyping(false)
      }, i * 80)
      timerRef.current.push(t)
    })
  }

  useEffect(() => () => timerRef.current.forEach(clearTimeout), [])

  return (
    <section
      aria-label="Demo"
      style={{ padding: "7rem 1.5rem" }}
    >
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <p
          style={{
            fontFamily: "'Geist Mono', monospace",
            fontSize: "0.6875rem",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#B4B2A9",
            marginBottom: "1.5rem",
          }}
        >
          {DEMO.eyebrow}
        </p>

        <h2
          style={{
            fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
            fontWeight: 500,
            letterSpacing: "-0.03em",
            marginBottom: "2.5rem",
            lineHeight: 1.2,
            whiteSpace: "pre-line",
          }}
        >
          {DEMO.heading}
        </h2>

        <div
          style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}
          className="demo-grid"
        >
          {DEMO.scenarios.map(s => {
            const tc = TAG_COLORS[s.tagColor]
            const isSelected = selected?.id === s.id
            return (
              <div
                key={s.id}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                onClick={() => runScenario(s)}
                onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); runScenario(s) } }}
                style={{
                  background: "#F8F8F7",
                  border: isSelected ? "1px solid #3C3489" : "1px solid rgba(0,0,0,0.07)",
                  boxShadow: isSelected ? "0 0 0 3px rgba(60,52,137,0.08)" : "none",
                  borderRadius: 16,
                  padding: "1.5rem",
                  cursor: "pointer",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    background: tc.bg,
                    color: tc.color,
                    borderRadius: 20,
                    fontSize: "0.6875rem",
                    fontFamily: "'Geist Mono', monospace",
                    padding: "3px 10px",
                    fontWeight: 500,
                  }}
                >
                  {s.tag}
                </span>
                <p style={{ fontSize: "1rem", fontWeight: 500, margin: "0.75rem 0 0.25rem" }}>
                  {s.title}
                </p>
                <p style={{ fontSize: "0.8125rem", color: "#5F5E5A", fontFamily: "'Geist Mono', monospace" }}>
                  {s.meta}
                </p>
                <button
                  onClick={e => { e.stopPropagation(); runScenario(s) }}
                  style={{
                    marginTop: "1rem",
                    fontSize: "0.8125rem",
                    color: "#3C3489",
                    fontWeight: 500,
                    background: "none",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  Run →
                </button>
              </div>
            )
          })}
        </div>

        {/* Terminal panel */}
        <div
          role="log"
          aria-live="polite"
          aria-label="Demo terminal output"
          style={{
            background: "#1A1A18",
            borderRadius: 16,
            padding: "1.5rem",
            marginTop: "1.5rem",
            minHeight: 160,
            fontFamily: "'Geist Mono', monospace",
            fontSize: "0.8125rem",
            lineHeight: 1.8,
          }}
        >
          {/* Traffic lights bar */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: "1rem" }}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57", display: "inline-block" }} />
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#FFBD2E", display: "inline-block" }} />
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#28C840", display: "inline-block" }} />
            <span style={{ marginLeft: 8, color: "#B4B2A9", fontSize: "0.75rem" }}>finsight — demo</span>
          </div>

          {lines.length === 0 && !typing ? (
            <span style={{ color: "#5F5E5A" }}>$ select a scenario above</span>
          ) : (
            lines.map((line, i) => (
              <div key={i}>{colorLine(line)}</div>
            ))
          )}
          {typing && <span style={{ color: "#5F5E5A" }}>▌</span>}
        </div>
      </div>

      <style>{`
        @media (max-width: 639px) { .demo-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </section>
  )
}
