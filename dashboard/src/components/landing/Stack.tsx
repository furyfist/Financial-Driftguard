import { useState } from "react"
import { STACK } from "../../lib/constants"

export function Stack() {
  const [hovered, setHovered] = useState<string | null>(null)

  return (
    <section
      aria-label="Technology stack"
      style={{ padding: "7rem 1.5rem" }}
    >
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
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
          {STACK.eyebrow}
        </p>

        <p
          style={{
            fontSize: "1.25rem",
            fontWeight: 500,
            color: "#2C2C2A",
            marginBottom: "2rem",
          }}
        >
          {STACK.oneliner}
        </p>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            marginBottom: "2rem",
          }}
        >
          {STACK.pills.map(pill => (
            <span
              key={pill}
              onMouseEnter={() => setHovered(pill)}
              onMouseLeave={() => setHovered(null)}
              style={{
                background: "#F8F8F7",
                border: hovered === pill ? "1px solid #3C3489" : "1px solid rgba(0,0,0,0.07)",
                borderRadius: 20,
                padding: "6px 18px",
                fontSize: "0.8125rem",
                color: hovered === pill ? "#3C3489" : "#5F5E5A",
                fontFamily: "'Geist Mono', monospace",
                transition: "border-color 0.15s ease, color 0.15s ease",
                cursor: "default",
              }}
            >
              {pill}
            </span>
          ))}
        </div>

        <a
          href={STACK.github}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            color: "#2C2C2A",
            fontSize: "0.9rem",
            fontWeight: 500,
            textDecoration: "none",
            borderBottom: "1px solid transparent",
            transition: "border-bottom-color 0.15s ease",
          }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.borderBottomColor = "#2C2C2A")}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.borderBottomColor = "transparent")}
        >
          View on GitHub ↗
        </a>
      </div>
    </section>
  )
}
