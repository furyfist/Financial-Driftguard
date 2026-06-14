import { useEffect, useRef, useState } from "react"
import { HOW_IT_WORKS } from "../../lib/constants"

function Step({ step, active }: { step: typeof HOW_IT_WORKS.steps[0]; active: boolean }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) { /* active is managed by parent */ }
      },
      { threshold: 0.5 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      style={{
        display: "grid",
        gridTemplateColumns: "56px 1fr",
        alignItems: "start",
        padding: "2rem 0",
        borderTop: "1px solid rgba(0,0,0,0.07)",
      }}
    >
      <span
        style={{
          fontFamily: "'Geist Mono', monospace",
          fontSize: "0.75rem",
          color: active ? "#3C3489" : "#B4B2A9",
          paddingTop: 4,
          transition: "color 0.3s ease",
        }}
      >
        {step.num}
      </span>
      <div>
        <p
          style={{
            fontSize: "1.125rem",
            fontWeight: 500,
            color: active ? "#000" : "#2C2C2A",
            marginBottom: 4,
            transition: "color 0.3s ease",
          }}
        >
          {step.title}
        </p>
        <p style={{ fontSize: "0.9375rem", color: "#5F5E5A", lineHeight: 1.6 }}>
          {step.body}
        </p>
      </div>
    </div>
  )
}

export function HowItWorks() {
  const [activeIdx, setActiveIdx] = useState(-1)
  const stepRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const observers = HOW_IT_WORKS.steps.map((_, i) => {
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActiveIdx(i) },
        { threshold: 0.5 }
      )
      if (stepRefs.current[i]) obs.observe(stepRefs.current[i]!)
      return obs
    })
    return () => observers.forEach(obs => obs.disconnect())
  }, [])

  return (
    <section
      aria-label="How it works"
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
          {HOW_IT_WORKS.eyebrow}
        </p>

        <h2
          style={{
            fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
            fontWeight: 500,
            letterSpacing: "-0.03em",
            marginBottom: "3rem",
            lineHeight: 1.2,
          }}
        >
          {HOW_IT_WORKS.heading}
        </h2>

        <div>
          {HOW_IT_WORKS.steps.map((step, i) => (
            <div key={step.num} ref={el => { stepRefs.current[i] = el }}>
              <Step step={step} active={activeIdx === i} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
