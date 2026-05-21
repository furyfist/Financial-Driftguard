"""Champion-challenger automation — compares current model state vs last stable baseline."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Conditions required to trigger a champion-challenger run.
# Only meaningful when drift cannot be explained by macro regime.
TRIGGER_REGIMES    = frozenset({"stable"})
TRIGGER_SEVERITIES = frozenset({"high", "critical"})

# Drift severities that qualify as a "stable" challenger baseline.
STABLE_SEVERITIES = frozenset({"none", "low"})

# Delta thresholds that determine the winner.
_DELTA_SIGNIFICANT = 0.10   # champion score > challenger score + this → challenger wins
_DELTA_NOISE       = 0.02   # within this band → inconclusive


@dataclass
class ChallengerResult:
    model_id: str
    status: str                         # completed | wrong_regime | wrong_severity | insufficient_data | no_baseline
    champion_run_id: int | None         = None
    challenger_run_id: int | None       = None
    champion_drift_score: float | None  = None
    challenger_drift_score: float | None = None
    champion_severity: str | None       = None
    challenger_severity: str | None     = None
    winner: str                         = "inconclusive"   # challenger_better | champion_better | inconclusive | no_baseline
    drift_score_delta: float | None     = None             # champion − challenger (positive = model decayed)
    drifted_features: list[str]         = field(default_factory=list)
    recommendation: str                 = ""
    triggered_at: datetime              = field(default_factory=lambda: datetime.now(timezone.utc))


class ChallengerRunner:
    """
    Compares the current (champion) drift run against the last stable (challenger) run.

    Trigger conditions:
      - Latest regime must be 'stable'  (drift is not macro-driven)
      - Latest drift severity must be 'high' or 'critical'

    If either condition is not met, a result with the appropriate status is returned
    without raising — callers always get a structured response.
    """

    def run(self, model_id: str) -> ChallengerResult:
        now    = datetime.now(timezone.utc)
        latest = _load_latest_run(model_id)

        if latest is None:
            return ChallengerResult(
                model_id=model_id,
                status="insufficient_data",
                recommendation="No drift runs found for this model.",
                triggered_at=now,
            )

        # Guard: regime must be stable
        regime = (latest.regime or "").lower()
        if regime not in TRIGGER_REGIMES:
            return ChallengerResult(
                model_id=model_id,
                status="wrong_regime",
                champion_run_id=latest.id,
                champion_drift_score=latest.drift_score,
                champion_severity=latest.overall_severity,
                recommendation=(
                    f"Champion-challenger skipped: current regime is '{regime or 'unknown'}', "
                    "not 'stable'. Drift may be macro-driven — do not retrain."
                ),
                triggered_at=now,
            )

        # Guard: severity must be high or critical
        severity = latest.overall_severity.lower()
        if severity not in TRIGGER_SEVERITIES:
            return ChallengerResult(
                model_id=model_id,
                status="wrong_severity",
                champion_run_id=latest.id,
                champion_drift_score=latest.drift_score,
                champion_severity=latest.overall_severity,
                recommendation=(
                    f"Champion-challenger skipped: current severity is '{severity}', "
                    "not 'high' or 'critical'. No significant drift to compare."
                ),
                triggered_at=now,
            )

        # Load last stable run as the challenger baseline
        challenger = _load_last_stable_run(model_id, before_id=latest.id)
        if challenger is None:
            return ChallengerResult(
                model_id=model_id,
                status="no_baseline",
                champion_run_id=latest.id,
                champion_drift_score=latest.drift_score,
                champion_severity=latest.overall_severity,
                winner="no_baseline",
                recommendation=(
                    "No stable baseline run found for comparison. "
                    "Run the model on clean data first to establish a champion baseline."
                ),
                triggered_at=now,
            )

        delta    = latest.drift_score - challenger.drift_score
        winner   = _determine_winner(delta)
        drifted  = _extract_drifted_features(latest.feature_results_json)
        rec      = _build_recommendation(winner, latest.drift_score, challenger.drift_score, delta, drifted)

        return ChallengerResult(
            model_id=model_id,
            status="completed",
            champion_run_id=latest.id,
            challenger_run_id=challenger.id,
            champion_drift_score=latest.drift_score,
            challenger_drift_score=challenger.drift_score,
            champion_severity=latest.overall_severity,
            challenger_severity=challenger.overall_severity,
            winner=winner,
            drift_score_delta=round(delta, 4),
            drifted_features=drifted,
            recommendation=rec,
            triggered_at=now,
        )


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _load_latest_run(model_id: str):
    from sqlmodel import Session, select, desc
    from driftguard.store.database import engine, DriftRun

    with Session(engine) as session:
        return session.exec(
            select(DriftRun)
            .where(DriftRun.model_id == model_id)
            .order_by(desc(DriftRun.checked_at))
            .limit(1)
        ).first()


def _load_last_stable_run(model_id: str, before_id: int):
    from sqlmodel import Session, select, desc
    from driftguard.store.database import engine, DriftRun

    with Session(engine) as session:
        return session.exec(
            select(DriftRun)
            .where(DriftRun.model_id == model_id)
            .where(DriftRun.id < before_id)
            .where(DriftRun.overall_severity.in_(list(STABLE_SEVERITIES)))
            .order_by(desc(DriftRun.checked_at))
            .limit(1)
        ).first()


# ── Pure logic helpers ─────────────────────────────────────────────────────────

def _determine_winner(delta: float) -> str:
    if delta > _DELTA_SIGNIFICANT:
        return "challenger_better"   # old stable model is better — current model decayed
    if delta < -_DELTA_NOISE:
        return "champion_better"     # current model is performing better
    return "inconclusive"


def _extract_drifted_features(feature_results_json: str) -> list[str]:
    try:
        features = json.loads(feature_results_json)
        return [
            f["feature_name"] for f in features
            if f.get("severity", "none") in ("medium", "high", "critical")
        ]
    except Exception:
        return []


def _build_recommendation(
    winner: str,
    champion_score: float,
    challenger_score: float,
    delta: float,
    drifted_features: list[str],
) -> str:
    features_str = (
        f" Top drifted features: {', '.join(drifted_features[:3])}."
        if drifted_features else ""
    )
    if winner == "challenger_better":
        return (
            f"Model decay confirmed: current drift score {champion_score:.3f} vs "
            f"stable baseline {challenger_score:.3f} (Δ+{delta:.3f}).{features_str} "
            "Recommend retraining against the stable baseline."
        )
    if winner == "champion_better":
        return (
            f"Current model outperforms stable baseline: "
            f"{champion_score:.3f} vs {challenger_score:.3f} (Δ{delta:.3f}). "
            "Drift may be transient — continue monitoring."
        )
    return (
        f"Scores comparable: current {champion_score:.3f} vs stable {challenger_score:.3f} "
        f"(Δ{delta:+.3f}).{features_str} No clear winner — continue monitoring."
    )
