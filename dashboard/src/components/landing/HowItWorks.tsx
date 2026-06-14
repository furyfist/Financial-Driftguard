import { useEffect, useRef, useState } from "react"
import { HOW_IT_WORKS } from "../../lib/constants"

export function HowItWorks() {
  const [activeIdx, setActiveIdx] = useState(0)
  const stepRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const observers = HOW_IT_WORKS.steps.map((_, i) => {
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActiveIdx(i) },
        { threshold: 0.6 }
      )
      if (stepRefs.current[i]) obs.observe(stepRefs.current[i]!)
      return obs
    })
    return () => observers.forEach(obs => obs.disconnect())
  }, [])

  const active = HOW_IT_WORKS.steps[activeIdx]

  return (
    <section aria-label="How it works" style={{ background: "#fff", borderBottom: "1px solid rgba(0,0,0,0.06)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "4.5rem 2rem" }}>

        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "0.75rem" }}>
          <span style={{
            fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem",
            letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9",
          }}>03</span>
          <span style={{
            fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem",
            letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9",
          }}>How it works</span>
        </div>

        <h2 style={{
          fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)", fontWeight: 600,
          letterSpacing: "-0.03em", marginBottom: "3rem", lineHeight: 1.25, color: "#2C2C2A",
        }}>
          {HOW_IT_WORKS.heading}
        </h2>

        {/* Desktop: step list left, active detail right */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3rem", alignItems: "start" }}
          className="hiw-grid">

          {/* Step list */}
          <div>
            {HOW_IT_WORKS.steps.map((step, i) => (
              <div
                key={step.num}
                ref={el => { stepRefs.current[i] = el }}
                onClick={() => setActiveIdx(i)}
                style={{
                  display: "grid", gridTemplateColumns: "40px 1fr",
                  gap: "1rem", alignItems: "start",
                  padding: "1.25rem 0",
                  borderTop: "1px solid rgba(0,0,0,0.07)",
                  cursor: "pointer",
                  opacity: activeIdx === i ? 1 : 0.45,
                  transition: "opacity 0.25s ease",
                }}
              >
                <span style={{
                  fontFamily: "'Geist Mono', monospace", fontSize: "0.75rem",
                  color: activeIdx === i ? "#3C3489" : "#B4B2A9",
                  paddingTop: 3, fontWeight: 600,
                  transition: "color 0.25s ease",
                }}>{step.num}</span>
                <div>
                  <p style={{
                    fontSize: "1rem", fontWeight: 600,
                    color: activeIdx === i ? "#2C2C2A" : "#5F5E5A",
                    transition: "color 0.25s ease",
                  }}>{step.title}</p>
                  <p style={{
                    fontSize: "0.875rem", color: "#5F5E5A", lineHeight: 1.6, marginTop: 4,
                    display: activeIdx === i ? "block" : "none",
                  }}>{step.body}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Active detail panel */}
          <div style={{
            background: "#F8F8F7", borderRadius: 12, padding: "2rem",
            border: "1px solid rgba(0,0,0,0.06)", position: "sticky", top: 72,
          }}>
            <div style={{
              fontFamily: "'Geist Mono', monospace", fontSize: "2.5rem", fontWeight: 700,
              color: "#3C3489", opacity: 0.12, lineHeight: 1, marginBottom: "0.75rem",
              letterSpacing: "-0.04em",
            }}>{active.num}</div>
            <h3 style={{
              fontSize: "1.25rem", fontWeight: 600, color: "#2C2C2A",
              letterSpacing: "-0.02em", marginBottom: "0.75rem",
            }}>{active.title}</h3>
            <p style={{ fontSize: "0.9375rem", color: "#5F5E5A", lineHeight: 1.7 }}>
              {active.body}
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 767px) {
          .hiw-grid { grid-template-columns: 1fr !important; }
          .hiw-grid > div:last-child { display: none !important; }
          .hiw-grid > div:first-child div p { display: block !important; }
        }
      `}</style>
    </section>
  )
}
