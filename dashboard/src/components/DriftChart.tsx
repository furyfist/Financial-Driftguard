import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, ReferenceArea,
} from "recharts"
import type { Regime } from "../types"

const DOT_COLOR: Record<string, string> = {
  stable:        "#1A6B3C",
  credit_stress: "#B45309",
  rate_shock:    "#B45309",
  black_swan:    "#C0200F",
  recession:     "#C0200F",
  unknown:       "#888888",
}

const BAND_FILL: Record<string, string> = {
  stable:        "rgba(26, 107, 60, 0.08)",
  credit_stress: "rgba(180, 83, 9, 0.08)",
  rate_shock:    "rgba(180, 83, 9, 0.08)",
  black_swan:    "rgba(192, 32, 15, 0.08)",
  recession:     "rgba(192, 32, 15, 0.08)",
  unknown:       "rgba(136, 136, 136, 0.04)",
}

interface Point {
  date: string
  score: number
  severity: string
  regime: string
}

function buildBands(data: Point[]) {
  if (!data.length) return []
  const bands: Array<{ x1: string; x2: string; regime: string }> = []
  let x1 = data[0].date
  let cur = data[0].regime

  for (let i = 1; i < data.length; i++) {
    if (data[i].regime !== cur) {
      bands.push({ x1, x2: data[i - 1].date, regime: cur })
      x1 = data[i].date
      cur = data[i].regime
    }
  }
  bands.push({ x1, x2: data[data.length - 1].date, regime: cur })
  return bands
}

interface Props {
  history: Array<{
    checked_at: string
    drift_score: number
    overall_severity: string
    regime: Regime | null
  }>
}

export function DriftChart({ history }: Props) {
  const data: Point[] = [...history].reverse().map(r => ({
    date:     new Date(r.checked_at).toLocaleDateString(),
    score:    r.drift_score,
    severity: r.overall_severity,
    regime:   r.regime ?? "unknown",
  }))

  const bands = buildBands(data)

  const renderDot = (props: any) => {
    const { cx, cy, payload } = props
    return (
      <circle
        key={`dot-${payload.date}`}
        cx={cx}
        cy={cy}
        r={4}
        fill={DOT_COLOR[payload.regime] ?? "#888"}
      />
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 32, bottom: 0, left: 0 }}>
        {bands.map((b, i) => (
          <ReferenceArea
            key={i}
            x1={b.x1}
            x2={b.x2}
            fill={BAND_FILL[b.regime] ?? "rgba(136,136,136,0.04)"}
            strokeOpacity={0}
          />
        ))}

        <XAxis dataKey="date" tick={{ fontSize: 10, fontFamily: "DM Mono" }} />
        <YAxis tick={{ fontSize: 10, fontFamily: "DM Mono" }} domain={[0, "auto"]} />

        <Tooltip
          contentStyle={{ fontFamily: "DM Mono", fontSize: 11, border: "1px solid #E8E6E0" }}
          formatter={(value: number, _: string, props: any) => [
            value.toFixed(4),
            `regime: ${props.payload?.regime ?? "—"} | ${props.payload?.severity}`,
          ]}
        />

        <ReferenceLine
          y={0.10}
          stroke="#888"
          strokeDasharray="3 3"
          strokeWidth={1}
          label={{ value: "PSI 0.10", fontSize: 9, fill: "#888", fontFamily: "DM Mono", position: "right" }}
        />

        <Line
          type="monotone"
          dataKey="score"
          stroke="#D4450C"
          strokeWidth={1.5}
          dot={renderDot}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
