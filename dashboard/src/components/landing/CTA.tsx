import { useState } from "react"
import { CTA as COPY } from "../../lib/constants"

export function CTA() {
  const [hovered, setHovered] = useState(false)

  return (
    <section
      aria-label="Call to action"
      style={{ padding: "0 1.5rem 7rem" }}
    >
      <div
        style={{
          background: "#26215C",
          borderRadius: 16,
          padding: "5rem 4rem",
        }}
        className="cta-block"
      >
        <h2
          style={{
            fontSize: "clamp(2rem, 4vw, 3.25rem)",
            fontWeight: 500,
            letterSpacing: "-0.03em",
            lineHeight: 1.15,
            marginBottom: "2.5rem",
          }}
        >
          <span style={{ color: "#ffffff" }}>{COPY.line1}</span>
          <br />
          <span style={{ color: "rgba(255,255,255,0.55)" }}>{COPY.line2}</span>
        </h2>

        <a
          href={COPY.href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Clone FinSight AI on GitHub"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          style={{
            display: "inline-block",
            background: hovered ? "#EEEDFE" : "#ffffff",
            color: "#26215C",
            borderRadius: 6,
            padding: "12px 28px",
            fontSize: "0.9375rem",
            fontWeight: 500,
            textDecoration: "none",
            transition: "background 0.2s ease",
          }}
        >
          {COPY.button}
        </a>
      </div>

      <style>{`
        @media (max-width: 639px) {
          .cta-block { padding: 3rem 2rem !important; margin: 0 -0.5rem; }
        }
      `}</style>
    </section>
  )
}
