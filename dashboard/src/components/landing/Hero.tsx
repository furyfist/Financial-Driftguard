import { useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"
import { HERO } from "../../lib/constants"

const REGIME_COLORS: Record<string, { bg: string; color: string; dot: string }> = {
  stable:        { bg: "#E1F5EE", color: "#0F6E56", dot: "#0F6E56" },
  credit_stress: { bg: "#FAEEDA", color: "#854F0B", dot: "#854F0B" },
  black_swan:    { bg: "#FCEBEB", color: "#A32D2D", dot: "#A32D2D" },
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
    <span
      aria-label={`regime: ${regime.label}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.bg}`,
        borderRadius: 20,
        fontSize: "0.75rem",
        fontFamily: "'Geist Mono', monospace",
        padding: "4px 14px",
        transition: "background 0.4s ease, color 0.4s ease",
      }}
    >
      <span style={{ color: c.dot, fontSize: "0.6rem" }}>●</span>
      regime: {regime.label}
    </span>
  )
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04 } },
}
const wordVariants = {
  hidden:  { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
}

function AnimatedHeadline() {
  const lines = [HERO.headline1, HERO.headline2, HERO.headline3]
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{ lineHeight: 1.1 }}
    >
      {lines.map((line, li) =>
        line.split(" ").map((word, wi) => (
          <motion.span
            key={`${li}-${wi}`}
            variants={wordVariants}
            style={{
              display: "inline-block",
              marginRight: "0.28em",
              fontSize: "clamp(2.5rem, 6vw, 5rem)",
              fontWeight: 500,
              letterSpacing: "-0.04em",
              color: li === 2 ? "#3C3489" : "#2C2C2A",
            }}
          >
            {word}
          </motion.span>
        ))
      ).reduce<React.ReactNode[]>((acc, words, li) => {
        if (li > 0) acc.push(<br key={`br-${li}`} />)
        acc.push(...(words as React.ReactNode[]))
        return acc
      }, [])}
    </motion.div>
  )
}

export function Hero() {
  return (
    <section
      aria-label="Hero"
      style={{
        minHeight: "100vh",
        paddingTop: 56,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          maxWidth: 800,
          margin: "0 auto",
          padding: "0 1.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "2rem",
        }}
      >
        <RegimeBadge />

        <AnimatedHeadline />

        <p
          style={{
            fontSize: "1.125rem",
            color: "#5F5E5A",
            maxWidth: 560,
            lineHeight: 1.65,
          }}
        >
          {HERO.subtext}
        </p>

        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <a
            href="/dashboard"
            style={{
              background: "#3C3489",
              color: "#fff",
              padding: "11px 28px",
              borderRadius: 6,
              fontSize: "0.9rem",
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            {HERO.ctaPrimary}
          </a>
          <a
            href="#"
            style={{
              color: "#5F5E5A",
              fontSize: "0.9rem",
              textDecoration: "none",
              borderBottom: "1px solid transparent",
            }}
            onMouseEnter={e => ((e.target as HTMLElement).style.borderBottomColor = "#5F5E5A")}
            onMouseLeave={e => ((e.target as HTMLElement).style.borderBottomColor = "transparent")}
          >
            {HERO.ctaSecondary}
          </a>
        </div>

        <div
          style={{
            borderTop: "1px solid rgba(0,0,0,0.08)",
            paddingTop: "1.5rem",
            fontFamily: "'Geist Mono', monospace",
            fontSize: "0.8125rem",
            color: "#5F5E5A",
          }}
        >
          {HERO.stats.join("  ·  ")}
        </div>
      </div>
    </section>
  )
}
