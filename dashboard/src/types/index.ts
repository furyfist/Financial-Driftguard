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

export interface MacroSnapshot {
  fetched_at: string
  vix: number | null
  credit_spread: number | null
  fed_funds_rate: number | null
  yield_curve: number | null
  unemployment_rate: number | null
  regime: Regime | null
  regime_confidence: number | null
}

export interface WebhookConfig {
  platform: "discord" | "slack"
  webhook_url: string
  model_id: string | null
  severity_threshold: "low" | "medium" | "high" | "critical"
}

export interface DriftForecast {
  probability: number
  expected_regime: Regime
  trigger_signals: string[]
  horizon_days: number
  explanation: string
}

export type ChallengerWinner =
  | "challenger_better"
  | "champion_better"
  | "inconclusive"
  | "no_baseline"

export interface ChallengerResult {
  model_id: string
  status: string
  champion_run_id: number | null
  challenger_run_id: number | null
  champion_drift_score: number | null
  challenger_drift_score: number | null
  champion_severity: Severity | null
  challenger_severity: Severity | null
  winner: ChallengerWinner
  drift_score_delta: number | null
  drifted_features: string[]
  recommendation: string
  triggered_at: string
}