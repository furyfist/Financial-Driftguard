import { FOOTER } from "../../lib/constants"

export function Footer() {
  return (
    <footer
      style={{
        padding: "2rem 1.5rem",
        borderTop: "1px solid rgba(0,0,0,0.06)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
      className="footer-inner"
    >
      <span
        style={{
          fontFamily: "'Geist Mono', monospace",
          fontSize: "0.8125rem",
          color: "#5F5E5A",
        }}
      >
        {FOOTER.wordmark}
      </span>
      <span
        style={{
          fontFamily: "'Geist Mono', monospace",
          fontSize: "0.8125rem",
          color: "#5F5E5A",
          textAlign: "right",
        }}
      >
        {FOOTER.right}
      </span>

      <style>{`
        @media (max-width: 639px) {
          .footer-inner { flex-direction: column !important; gap: 0.75rem; text-align: center; }
          .footer-inner span { text-align: center !important; }
        }
      `}</style>
    </footer>
  )
}
