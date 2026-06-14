import { PROBLEM } from "../../lib/constants"

export function Problem() {
  return (
    <section aria-label="Problem" style={{ background: "#F8F8F7" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "4.5rem 2rem" }}>

        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "0.75rem" }}>
          <span style={{
            fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem",
            letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9",
          }}>
            02
          </span>
          <span style={{
            fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem",
            letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9",
          }}>
            The Problem
          </span>
        </div>

        <h2 style={{
          fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)", fontWeight: 600,
          letterSpacing: "-0.03em", maxWidth: 680, marginBottom: "2.5rem", lineHeight: 1.25,
          color: "#2C2C2A",
        }}>
          {PROBLEM.heading}
        </h2>

        {/* Two-col cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}
          className="problem-grid">

          <div style={{
            background: "#fff", border: "1px solid rgba(163,45,45,0.15)",
            borderTop: "3px solid #A32D2D",
            borderRadius: 10, padding: "1.5rem",
          }}>
            <p style={{
              fontSize: "0.6875rem", fontWeight: 600, color: "#A32D2D",
              textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1rem",
            }}>
              {PROBLEM.leftCard.title}
            </p>
            <p style={{
              fontSize: "1rem", color: "#2C2C2A", lineHeight: 1.7,
              whiteSpace: "pre-line", fontFamily: "'Geist Mono', monospace",
            }}>
              {PROBLEM.leftCard.body}
            </p>
          </div>

          <div style={{
            background: "#fff", border: "1px solid rgba(0,0,0,0.08)",
            borderTop: "3px solid #B4B2A9",
            borderRadius: 10, padding: "1.5rem",
          }}>
            <p style={{
              fontSize: "0.6875rem", fontWeight: 600, color: "#5F5E5A",
              textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1rem",
            }}>
              {PROBLEM.rightCard.title}
            </p>
            <p style={{ fontSize: "1rem", color: "#2C2C2A", lineHeight: 1.7 }}>
              {PROBLEM.rightCard.body}
            </p>
          </div>
        </div>

        {/* Pull quote */}
        <div style={{
          marginTop: "2rem", padding: "1.25rem 1.5rem",
          background: "#fff", borderRadius: 10,
          border: "1px solid rgba(0,0,0,0.07)",
          borderLeft: "3px solid #3C3489",
          display: "flex", gap: "1rem", alignItems: "flex-start",
        }}>
          <span style={{ color: "#3C3489", fontSize: "1.25rem", lineHeight: 1, flexShrink: 0 }}>"</span>
          <p style={{ fontSize: "0.9375rem", color: "#5F5E5A", lineHeight: 1.7, margin: 0 }}>
            {PROBLEM.pullQuote.split("int_rate").map((part, i) =>
              i === 0 ? <span key={i}>{part}</span> : (
                <span key={i}>
                  <code style={{
                    fontFamily: "'Geist Mono', monospace", background: "#F1EFE8",
                    padding: "1px 5px", borderRadius: 4, fontSize: "0.875rem",
                  }}>int_rate</code>
                  {part}
                </span>
              )
            )}
          </p>
        </div>

      </div>

      <style>{`
        @media (max-width: 639px) { .problem-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </section>
  )
}
