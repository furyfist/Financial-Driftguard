"use client"
import { useEffect, useRef, useState } from "react"
import { NAV } from "../../lib/constants"

export function Nav() {
  const [visible, setVisible] = useState(true)
  const lastY = useRef(0)

  useEffect(() => {
    let rafId: number
    const onScroll = () => {
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        const y = window.scrollY
        if (y < 100) { setVisible(true) }
        else if (y > lastY.current) { setVisible(false) }
        else { setVisible(true) }
        lastY.current = y
      })
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(rafId) }
  }, [])

  return (
    <nav
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: 56,
        zIndex: 50,
        background: "rgba(255,255,255,0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(0,0,0,0.06)",
        transform: visible ? "translateY(0)" : "translateY(-100%)",
        transition: "transform 0.25s ease",
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "0 1.5rem",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <a
          href="/"
          style={{
            fontFamily: "var(--font-mono, 'Geist Mono', monospace)",
            fontWeight: 500,
            fontSize: "0.9rem",
            color: "#3C3489",
            textDecoration: "none",
          }}
        >
          {NAV.wordmark}
        </a>

        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
          <a
            href={NAV.github}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View on GitHub"
            className="hide-on-mobile"
            style={{
              fontSize: "0.85rem",
              color: "#5F5E5A",
              textDecoration: "none",
            }}
          >
            GitHub ↗
          </a>
          <a
            href={NAV.ctaHref}
            aria-label="Go to the dashboard"
            style={{
              background: "#3C3489",
              color: "#fff",
              borderRadius: 6,
              padding: "6px 16px",
              fontSize: "0.8125rem",
              fontWeight: 500,
              textDecoration: "none",
              whiteSpace: "nowrap",
            }}
          >
            {NAV.cta}
          </a>
        </div>
      </div>

      <style>{`
        @media (max-width: 639px) { .hide-on-mobile { display: none !important; } }
      `}</style>
    </nav>
  )
}
