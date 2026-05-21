from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ...scheduler.jobs import load_baseline, run_drift_check
from ...regime.macro_signals import MacroSnapshot

router = APIRouter(prefix="/demo", tags=["demo"])

_SCENARIOS: dict[str, MacroSnapshot] = {
    "rate_hike_q4_2018": MacroSnapshot(
        as_of=date(2018, 12, 31),
        vix=18.5,
        credit_spread=1.35,
        fed_funds_rate=2.25,
        yield_curve=0.21,
        unemployment_rate=3.7,
    ),
    "covid_crash_march_2020": MacroSnapshot(
        as_of=date(2020, 3, 31),
        vix=65.0,
        credit_spread=3.70,
        fed_funds_rate=0.25,
        yield_curve=0.52,
        unemployment_rate=4.4,
    ),
    "normal_model_decay": MacroSnapshot(
        as_of=date(2024, 1, 1),
        vix=14.0,
        credit_spread=0.90,
        fed_funds_rate=5.25,
        yield_curve=-0.48,
        unemployment_rate=3.8,
    ),
}


@router.post("/scenarios/{scenario_name}")
def run_demo_scenario(
    scenario_name: str,
    model_id: str = Query(default="lending_club_v1"),
):
    """Run a named demo scenario against the registered baseline and return the drift result."""
    macro = _SCENARIOS.get(scenario_name)
    if macro is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario_name}'. Valid: {list(_SCENARIOS)}",
        )

    baseline = load_baseline(model_id)
    if baseline is None:
        raise HTTPException(
            status_code=400,
            detail=f"No baseline registered for '{model_id}'. POST /drift/{model_id}/run with set_as_baseline=true first.",
        )

    result = run_drift_check(model_id, baseline, macro=macro)
    if result is None:
        raise HTTPException(status_code=500, detail="Drift check returned no result.")

    return {
        "model_id":         model_id,
        "scenario":         scenario_name,
        "overall_severity": result.overall_severity.value,
        "drift_score":      result.drift_score,
        "regime":           result.regime,
        "notes":            result.notes,
        "drifted_features": [
            {"feature": f.feature_name, "detector": f.detector, "score": f.score}
            for f in result.drifted_features
        ],
    }
