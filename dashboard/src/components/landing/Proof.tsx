import { useEffect, useRef, useState } from "react"
import { PROOF } from "../../lib/constants"

function CountUp({ target, suffix, decimals }: { target: number; suffix: string; decimals: number }) {
  const [val, setVal] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const started = useRef(false)
  const prefersReduced = typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true
        if (prefersReduced) { setVal(target); return }
        const duration = 1000
        const start = performance.now()
        const step = (now: number) => {
          const t = Math.min((now - start) / duration, 1)
          setVal(target * t)
          if (t < 1) requestAnimationFrame(step)
          else setVal(target)
        }
        requestAnimationFrame(step)
      }
    }, { threshold: 0.5 })
    obs.observe(el)
    return () => obs.disconnect()
  }, [target, decimals, prefersReduced])

  const display = decimals === 3
    ? val.toFixed(3)
    : decimals === 1
    ? val.toFixed(1)
    : Math.round(val).toString()

  return (
    <div ref={ref}>
      <p
        style={{
          fontFamily: "'Geist Mono', monospace",
          fontSize: "clamp(2rem, 4vw, 3rem)",
          fontWeight: 500,
          color: "#2C2C2A",
          letterSpacing: "-0.03em",
          marginBottom: "0.75rem",
          paddingBottom: "0.75rem",
          borderBottom: "1px solid rgba(0,0,0,0.08)",
        }}
      >
        {display}{suffix}
      </p>
    </div>
  )
}

export function Proof() {
  return (
    <section
      aria-label="Proof metrics"
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
          {PROOF.eyebrow}
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
          {PROOF.heading}
        </h2>

        <div
          style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1.5rem" }}
          className="proof-grid"
        >
          {PROOF.stats.map(stat => (
            <div key={stat.label}>
              <CountUp target={stat.value} suffix={stat.suffix} decimals={stat.decimals} />
              <p style={{ fontSize: "0.8125rem", color: "#5F5E5A", lineHeight: 1.5 }}>
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @media (max-width: 767px) { .proof-grid { grid-template-columns: repeat(2, 1fr) !important; } }
      `}</style>
    </section>
  )
}
