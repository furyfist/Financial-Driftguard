import { useEffect, useRef, useState } from "react"
import { PROOF } from "../../lib/constants"

const STAT_ACCENTS = ["#2D8C5A", "#0F6E56", "#854F0B", "#A32D2D"]

function CountUp({ target, suffix, decimals }: { target: number; suffix: string; decimals: number }) {
  const [val, setVal] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
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
        const duration = 1200
        const start = performance.now()
        const step = (now: number) => {
          const t = Math.min((now - start) / duration, 1)
          const eased = 1 - Math.pow(1 - t, 3)
          setVal(target * eased)
          if (t < 1) requestAnimationFrame(step)
          else setVal(target)
        }
        requestAnimationFrame(step)
      }
    }, { threshold: 0.4 })
    obs.observe(el)
    return () => obs.disconnect()
  }, [target, prefersReduced])

  const display = decimals === 3 ? val.toFixed(3)
    : decimals === 1 ? val.toFixed(1)
    : Math.round(val).toString()

  return <span ref={ref}>{display}{suffix}</span>
}

export function Proof() {
  return (
    <section aria-label="Proof metrics" style={{ background: "#fff", borderBottom: "1px solid rgba(0,0,0,0.06)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "4.5rem 2rem" }}>

        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem", marginBottom: "0.75rem" }}>
          <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9" }}>05</span>
          <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: "0.6875rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#B4B2A9" }}>Proof</span>
        </div>

        <h2 style={{
          fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)", fontWeight: 600,
          letterSpacing: "-0.03em", marginBottom: "2.5rem", lineHeight: 1.25, color: "#2C2C2A",
        }}>{PROOF.heading}</h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0 }}
          className="proof-grid">
          {PROOF.stats.map((stat, i) => (
            <div key={stat.label} style={{
              padding: "1.5rem 1.5rem 1.5rem 0",
              borderLeft: i > 0 ? "1px solid rgba(0,0,0,0.07)" : "none",
              paddingLeft: i > 0 ? "1.5rem" : 0,
            }}>
              <div style={{
                fontFamily: "'Geist Mono', monospace",
                fontSize: "clamp(2rem, 3.5vw, 3rem)",
                fontWeight: 700, color: STAT_ACCENTS[i],
                letterSpacing: "-0.04em", lineHeight: 1,
                marginBottom: "0.75rem",
              }}>
                <CountUp target={stat.value} suffix={stat.suffix} decimals={stat.decimals} />
              </div>
              <p style={{ fontSize: "0.8125rem", color: "#5F5E5A", lineHeight: 1.5 }}>
                {stat.label}
              </p>
            </div>
          ))}
        </div>

      </div>

      <style>{`
        @media (max-width: 767px) {
          .proof-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .proof-grid > div { border-left: none !important; padding-left: 0 !important; border-top: 1px solid rgba(0,0,0,0.07); padding-top: 1.5rem; }
        }
      `}</style>
    </section>
  )
}
