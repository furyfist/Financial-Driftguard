import { FOOTER } from "../../lib/constants"

export function Footer() {
  return (
    <footer style={{
      background: "#124028",
      borderTop: "1px solid rgba(255,255,255,0.07)",
    }}>
      <div style={{
        maxWidth: 1100, margin: "0 auto", padding: "1.5rem 2rem",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }} className="footer-inner">
        <span style={{
          fontFamily: "'Geist Mono', monospace", fontSize: "0.8125rem",
          color: "rgba(255,255,255,0.35)", fontWeight: 500,
        }}>
          {FOOTER.wordmark}
        </span>
        <span style={{
          fontFamily: "'Geist Mono', monospace", fontSize: "0.75rem",
          color: "rgba(255,255,255,0.25)",
        }}>
          {FOOTER.right}
        </span>
      </div>

      <style>{`
        @media (max-width: 639px) {
          .footer-inner { flex-direction: column !important; gap: 0.5rem; text-align: center; padding: 1.25rem 1.5rem !important; }
        }
      `}</style>
    </footer>
  )
}
