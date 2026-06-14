import { CTA as COPY } from "../../lib/constants"

export function CTA() {
  return (
    <section aria-label="Call to action" style={{ background: "#1A5C3A" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "5rem 2rem" }}>

        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "3rem", alignItems: "center" }}
          className="cta-grid">

          <div>
            <p style={{
              fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem",
              letterSpacing: "0.12em", textTransform: "uppercase",
              color: "rgba(255,255,255,0.3)", marginBottom: "1rem",
            }}>Financial DriftGuard</p>
            <h2 style={{
              fontSize: "clamp(2rem, 4vw, 3.25rem)", fontWeight: 600,
              letterSpacing: "-0.03em", lineHeight: 1.12, margin: 0,
            }}>
              <span style={{ color: "#fff" }}>{COPY.line1}</span><br />
              <span style={{ color: "rgba(255,255,255,0.45)" }}>{COPY.line2}</span>
            </h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", flexShrink: 0 }}>
            <a href="/dashboard"
              aria-label="Open the live dashboard"
              style={{
                background: "#fff", color: "#1A5C3A",
                borderRadius: 8, padding: "13px 28px",
                fontSize: "0.9375rem", fontWeight: 700,
                textDecoration: "none", textAlign: "center",
                letterSpacing: "-0.01em", whiteSpace: "nowrap",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "#E1F5EE")}
              onMouseLeave={e => (e.currentTarget.style.background = "#fff")}
            >
              Open Dashboard →
            </a>
            <a href={COPY.href} target="_blank" rel="noopener noreferrer"
              aria-label="Clone Financial DriftGuard on GitHub"
              style={{
                background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 8, padding: "12px 28px",
                fontSize: "0.875rem", fontWeight: 500,
                textDecoration: "none", textAlign: "center", whiteSpace: "nowrap",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.14)"; e.currentTarget.style.color = "#fff" }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "rgba(255,255,255,0.7)" }}
            >
              {COPY.button}
            </a>
          </div>
        </div>

      </div>

      <style>{`
        @media (max-width: 767px) {
          .cta-grid { grid-template-columns: 1fr !important; gap: 2rem !important; }
          .cta-grid > div:last-child { flex-direction: row !important; flex-wrap: wrap; }
        }
      `}</style>
    </section>
  )
}
