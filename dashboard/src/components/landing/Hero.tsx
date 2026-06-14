import { useEffect, useRef, useState } from "react"
import { motion, type Variants } from "framer-motion"
import { HERO } from "../../lib/constants"

const REGIME_COLORS: Record<string, { bg: string; color: string; border: string }> = {
  stable:        { bg: "#E1F5EE", color: "#0F6E56", border: "rgba(15,110,86,0.2)" },
  credit_stress: { bg: "#FAEEDA", color: "#854F0B", border: "rgba(133,79,11,0.2)" },
  black_swan:    { bg: "#FCEBEB", color: "#A32D2D", border: "rgba(163,45,45,0.2)" },
}

function RegimeBadge() {
  const [idx, setIdx] = useState(0)
  const prefersReduced = useRef(
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  )

  useEffect(() => {
    if (prefersReduced.current) return
    const t = setTimeout(() => {
      const id = setInterval(() => setIdx(i => (i + 1) % HERO.regimes.length), 2500)
      return () => clearInterval(id)
    }, 500)
    return () => clearTimeout(t)
  }, [])

  const regime = HERO.regimes[idx]
  const c = REGIME_COLORS[regime.label]

  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 8,
      background: c.bg, border: `1px solid ${c.border}`,
      borderRadius: 8, padding: "6px 12px",
      transition: "background 0.4s ease, border-color 0.4s ease",
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%", background: c.color,
        display: "inline-block", flexShrink: 0,
      }} aria-hidden />
      <span style={{
        fontFamily: "'Geist Mono', monospace", fontSize: "0.75rem",
        color: c.color, fontWeight: 500,
      }} aria-label={`current regime: ${regime.label}`}>
        regime: {regime.label}
      </span>
    </div>
  )
}

const containerVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
}
const wordVariants: Variants = {
  hidden:  { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
}

export function Hero() {
  return (
    <section aria-label="Hero" style={{
      minHeight: "88vh", paddingTop: 52,
      display: "flex", alignItems: "center",
      borderBottom: "1px solid rgba(0,0,0,0.06)",
    }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "3rem 2rem", width: "100%" }}>

        {/* Top badge row */}
        <div style={{ marginBottom: "2rem" }}>
          <RegimeBadge />
        </div>

        {/* Headline */}
        <motion.h1
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          style={{ margin: 0, padding: 0 }}
        >
          {[HERO.headline1, HERO.headline2, HERO.headline3].map((line, li) => (
            <div key={li} style={{ overflow: "hidden", lineHeight: 1.05 }}>
              {line.split(" ").map((word, wi) => (
                <motion.span
                  key={`${li}-${wi}`}
                  variants={wordVariants}
                  style={{
                    display: "inline-block",
                    marginRight: "0.25em",
                    fontSize: "clamp(2.75rem, 6.5vw, 5.5rem)",
                    fontWeight: 600,
                    letterSpacing: "-0.04em",
                    color: li === 2 ? "#2D8C5A" : "#2C2C2A",
                    lineHeight: 1.05,
                  }}
                >
                  {word}
                </motion.span>
              ))}
            </div>
          ))}
        </motion.h1>

        {/* Subtext + CTAs — two-col on desktop */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr auto",
          gap: "2rem",
          alignItems: "end",
          marginTop: "2.5rem",
        }} className="hero-bottom">
          <div>
            <p style={{
              fontSize: "1.125rem", color: "#5F5E5A",
              maxWidth: 520, lineHeight: 1.65, margin: "0 0 1.75rem",
            }}>
              {HERO.subtext}
            </p>
            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <a href="/dashboard" style={{
                background: "#2D8C5A", color: "#fff",
                padding: "11px 26px", borderRadius: 8,
                fontSize: "0.9rem", fontWeight: 600,
                textDecoration: "none", letterSpacing: "-0.01em",
              }}>
                {HERO.ctaPrimary}
              </a>
              <a href={NAV_GITHUB} target="_blank" rel="noopener noreferrer" style={{
                color: "#5F5E5A", fontSize: "0.9rem",
                textDecoration: "none", display: "flex", alignItems: "center", gap: 4,
              }}
                onMouseEnter={e => (e.currentTarget.style.color = "#2C2C2A")}
                onMouseLeave={e => (e.currentTarget.style.color = "#5F5E5A")}
              >
                View on GitHub ↗
              </a>
            </div>
          </div>

          {/* Stats block — right side on desktop */}
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0",
            borderLeft: "1px solid rgba(0,0,0,0.08)",
            paddingLeft: "2rem", flexShrink: 0,
          }} className="hero-stats">
            {HERO.stats.map((stat, i) => {
              const [val, label] = stat.split(" ")
              return (
                <div key={i} style={{
                  padding: "0.75rem 1.25rem 0.75rem 0",
                  borderBottom: i < HERO.stats.length - 1 ? "1px solid rgba(0,0,0,0.06)" : "none",
                }}>
                  <div style={{
                    fontFamily: "'Geist Mono', monospace",
                    fontSize: "1.25rem", fontWeight: 600, color: "#2C2C2A",
                    letterSpacing: "-0.03em",
                  }}>{val}</div>
                  <div style={{ fontSize: "0.75rem", color: "#5F5E5A", marginTop: 2 }}>{label}</div>
                </div>
              )
            })}
          </div>
        </div>

      </div>

      <style>{`
        @media (max-width: 767px) {
          .hero-bottom { grid-template-columns: 1fr !important; }
          .hero-stats { border-left: none !important; padding-left: 0 !important; border-top: 1px solid rgba(0,0,0,0.08); padding-top: 1.5rem; }
        }
      `}</style>
    </section>
  )
}

// pulled from constants to avoid circular
const NAV_GITHUB = "https://github.com/himanshuraimau/financial-driftguard"
