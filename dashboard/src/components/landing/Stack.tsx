import { useState } from "react"
import { STACK } from "../../lib/constants"

export function Stack() {
  const [hovered, setHovered] = useState<string | null>(null)

  return (
    <section aria-label="Technology stack" style={{ background: "#F8F8F7", borderBottom: "1px solid rgba(0,0,0,0.06)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "4.5rem 2rem" }}>

        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "0.75rem" }}>
          <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9" }}>06</span>
          <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9" }}>Built with</span>
        </div>

        {/* Two-col: copy left, pills right */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "4rem", alignItems: "start" }}
          className="stack-grid">

          <div>
            <h2 style={{
              fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)", fontWeight: 600,
              letterSpacing: "-0.03em", lineHeight: 1.25, color: "#2C2C2A", marginBottom: "1rem",
            }}>
              {STACK.oneliner}
            </h2>
            <p style={{ fontSize: "0.9375rem", color: "#5F5E5A", lineHeight: 1.65, marginBottom: "1.75rem" }}>
              Purpose-built stack, no fluff. Every tool chosen for latency, accuracy, or explainability.
            </p>
            <a href={STACK.github} target="_blank" rel="noopener noreferrer"
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "#2C2C2A", color: "#fff", borderRadius: 8,
                padding: "10px 20px", fontSize: "0.875rem", fontWeight: 600,
                textDecoration: "none", letterSpacing: "-0.01em",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "#3C3489")}
              onMouseLeave={e => (e.currentTarget.style.background = "#2C2C2A")}
            >
              View on GitHub ↗
            </a>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignContent: "flex-start" }}>
            {STACK.pills.map(pill => (
              <span
                key={pill}
                onMouseEnter={() => setHovered(pill)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  background: hovered === pill ? "#3C3489" : "#fff",
                  border: hovered === pill ? "1px solid #3C3489" : "1px solid rgba(0,0,0,0.1)",
                  borderRadius: 8, padding: "7px 16px",
                  fontSize: "0.8125rem",
                  color: hovered === pill ? "#fff" : "#2C2C2A",
                  fontFamily: "'Geist Mono', monospace",
                  fontWeight: 500,
                  transition: "all 0.15s ease",
                  cursor: "default",
                  letterSpacing: "-0.01em",
                }}
              >{pill}</span>
            ))}
          </div>
        </div>

      </div>

      <style>{`
        @media (max-width: 767px) { .stack-grid { grid-template-columns: 1fr !important; gap: 2rem !important; } }
      `}</style>
    </section>
  )
}
