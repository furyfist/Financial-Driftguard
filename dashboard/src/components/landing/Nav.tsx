import { useEffect, useRef, useState } from "react"
import { NAV } from "../../lib/constants"

export function Nav() {
  const [visible, setVisible] = useState(true)
  const [scrolled, setScrolled] = useState(false)
  const lastY = useRef(0)

  useEffect(() => {
    let rafId: number
    const onScroll = () => {
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        const y = window.scrollY
        setScrolled(y > 20)
        if (y < 100) setVisible(true)
        else if (y > lastY.current) setVisible(false)
        else setVisible(true)
        lastY.current = y
      })
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(rafId) }
  }, [])

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, height: 52, zIndex: 50,
      background: scrolled ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.0)",
      backdropFilter: scrolled ? "blur(16px)" : "none",
      borderBottom: scrolled ? "1px solid rgba(0,0,0,0.07)" : "1px solid transparent",
      transform: visible ? "translateY(0)" : "translateY(-100%)",
      transition: "transform 0.25s ease, background 0.3s ease, border-color 0.3s ease",
    }}>
      <div style={{
        maxWidth: 1100, margin: "0 auto", padding: "0 2rem",
        height: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        {/* Wordmark */}
        <a href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            width: 26, height: 26, borderRadius: 6, background: "#2D8C5A",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.7rem", fontWeight: 700, color: "#fff",
            fontFamily: "'Geist Mono', monospace", letterSpacing: "-0.02em", flexShrink: 0,
          }}>DG</span>
          <span style={{
            fontFamily: "'Geist', sans-serif", fontWeight: 600,
            fontSize: "0.875rem", color: "#2C2C2A", letterSpacing: "-0.01em",
          }}>Financial <span style={{ color: "#2D8C5A" }}>DriftGuard</span></span>
        </a>

        {/* Right side */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <a href={NAV.github} target="_blank" rel="noopener noreferrer"
            className="nav-ghost-link"
            aria-label="View on GitHub"
            style={{ fontSize: "0.8125rem", color: "#5F5E5A", textDecoration: "none" }}>
            GitHub ↗
          </a>
          <a href={NAV.ctaHref} aria-label="Open the dashboard"
            style={{
              background: "#2D8C5A", color: "#fff", borderRadius: 6,
              padding: "7px 18px", fontSize: "0.8125rem", fontWeight: 500,
              textDecoration: "none", whiteSpace: "nowrap", letterSpacing: "-0.01em",
            }}>
            {NAV.cta}
          </a>
        </div>
      </div>

      <style>{`
        @media (max-width: 639px) { .nav-ghost-link { display: none !important; } }
      `}</style>
    </nav>
  )
}
