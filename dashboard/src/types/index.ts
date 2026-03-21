export type Severity = "none" | "low" | "medium" | "high" | "critical"
export type Regime =
  | "stable"
  | "rate_shock"
  | "recession"
  | "credit_stress"
  | "black_swan"
  | "unknown"

export interface Model {
  model_id: string
  description: string
  created_at: string
}

export interface DriftRun {
  id: number
  model_id: string
  checked_at: string
  overall_severity: Severity
  drift_score: number
  regime: Regime | null
  notes: string
}

export interface FeatureResult {
  feature_name: string
  detector: string
  score: number
  severity: Severity
  p_value: number | null
}

export interface Alert {
  id: number
  model_id: string
  severity: Severity
  message: string
  acknowledged: boolean
  created_at: string
}