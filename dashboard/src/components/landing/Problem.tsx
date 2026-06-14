import { PROBLEM } from "../../lib/constants"

export function Problem() {
  return (
    <section
      aria-label="Problem"
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
          {PROBLEM.eyebrow}
        </p>

        <h2
          style={{
            fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
            fontWeight: 500,
            letterSpacing: "-0.03em",
            maxWidth: 640,
            marginBottom: "3rem",
            lineHeight: 1.2,
          }}
        >
          {PROBLEM.heading}
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "1.5rem",
          }}
          className="problem-grid"
        >
          <div
            style={{
              background: "#FCEBEB",
              border: "1px solid rgba(163,45,45,0.12)",
              borderRadius: 16,
              padding: "2rem",
            }}
          >
            <p
              style={{
                fontSize: "0.75rem",
                fontWeight: 500,
                color: "#A32D2D",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: "1rem",
              }}
            >
              {PROBLEM.leftCard.title}
            </p>
            <p
              style={{
                fontSize: "1.0625rem",
                color: "#2C2C2A",
                lineHeight: 1.6,
                whiteSpace: "pre-line",
              }}
            >
              {PROBLEM.leftCard.body}
            </p>
          </div>

          <div
            style={{
              background: "#F1EFE8",
              border: "1px solid rgba(0,0,0,0.06)",
              borderRadius: 16,
              padding: "2rem",
            }}
          >
            <p
              style={{
                fontSize: "0.75rem",
                fontWeight: 500,
                color: "#5F5E5A",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: "1rem",
              }}
            >
              {PROBLEM.rightCard.title}
            </p>
            <p style={{ fontSize: "1.0625rem", color: "#2C2C2A", lineHeight: 1.6 }}>
              {PROBLEM.rightCard.body}
            </p>
          </div>
        </div>

        <blockquote
          style={{
            borderLeft: "3px solid #3C3489",
            paddingLeft: "1.5rem",
            marginTop: "3rem",
            fontSize: "1.0625rem",
            color: "#5F5E5A",
            lineHeight: 1.7,
          }}
        >
          {PROBLEM.pullQuote.split("int_rate").map((part, i) =>
            i === 0 ? (
              <span key={i}>{part}</span>
            ) : (
              <span key={i}>
                <code
                  style={{
                    fontFamily: "'Geist Mono', monospace",
                    background: "#F1EFE8",
                    padding: "1px 6px",
                    borderRadius: 4,
                  }}
                >
                  int_rate
                </code>
                {part}
              </span>
            )
          )}
        </blockquote>
      </div>

      <style>{`
        @media (max-width: 639px) { .problem-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </section>
  )
}
