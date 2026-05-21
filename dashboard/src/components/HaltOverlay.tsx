import { useEffect, useState } from "react"

interface Props {
  runId: number
  regime: string | null
}

export function HaltOverlay({ runId, regime }: Props) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (regime !== "black_swan") return

    const key = `halt_seen_${runId}`
    if (localStorage.getItem(key)) return

    localStorage.setItem(key, "1")
    setVisible(true)

    const timer = setTimeout(() => setVisible(false), 2000)
    return () => clearTimeout(timer)
  }, [runId, regime])

  if (!visible) return null

  return (
    <>
      <style>{`
        @keyframes halt-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(192, 32, 15, 0.5); }
          50%       { box-shadow: 0 0 0 20px rgba(192, 32, 15, 0); }
        }
        .halt-fade {
          animation: halt-fade-in 0.15s ease-out;
        }
        @keyframes halt-fade-in {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>

      <div
        className="halt-fade fixed inset-0 z-50 flex items-center justify-center"
        style={{ backgroundColor: "rgba(0, 0, 0, 0.92)" }}
      >
        <div
          className="flex flex-col items-center gap-5 rounded-2xl px-20 py-14"
          style={{
            border: "4px solid #C0200F",
            animation: "halt-pulse 0.8s ease-in-out infinite",
          }}
        >
          <span
            style={{
              fontFamily: "Bricolage Grotesque, sans-serif",
              fontSize: 120,
              fontWeight: 700,
              color: "#C0200F",
              lineHeight: 1,
            }}
          >
            HALT
          </span>
          <span
            style={{
              fontFamily: "DM Mono, monospace",
              fontSize: 18,
              color: "#ffffff",
              textAlign: "center",
              maxWidth: 480,
            }}
          >
            Black swan regime detected. All automated decisions frozen.
          </span>
        </div>
      </div>
    </>
  )
}
