"""Agent tools for champion-challenger experiments."""

import logging

logger = logging.getLogger(__name__)

EXPERIMENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "trigger_champion_challenger",
            "description": (
                "Trigger a champion-challenger comparison for a model. "
                "Compares the current (champion) drift state against the last stable "
                "(challenger) baseline to determine if the model has decayed. "
                "Only meaningful when regime is 'stable' and drift is 'high' or 'critical'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "The model ID to run the champion-challenger comparison for.",
                    }
                },
                "required": ["model_id"],
            },
        },
    },
]


def call_experiment_tool(name: str, arguments: dict) -> dict:
    """Dispatch an experiment tool call by name."""
    if name == "trigger_champion_challenger":
        return _trigger_champion_challenger(arguments.get("model_id", ""))
    logger.warning("Unknown experiment tool: %r", name)
    return {"error": f"Unknown experiment tool: {name!r}"}


def _trigger_champion_challenger(model_id: str) -> dict:
    """Run champion-challenger comparison and return structured result."""
    if not model_id:
        return {"error": "model_id is required"}
    try:
        from finsight.challenger import ChallengerRunner
        result = ChallengerRunner().run(model_id)
        return {
            "model_id":               result.model_id,
            "status":                 result.status,
            "winner":                 result.winner,
            "champion_drift_score":   result.champion_drift_score,
            "challenger_drift_score": result.challenger_drift_score,
            "drift_score_delta":      result.drift_score_delta,
            "champion_severity":      result.champion_severity,
            "drifted_features":       result.drifted_features,
            "recommendation":         result.recommendation,
        }
    except Exception as exc:
        logger.error("Champion-challenger failed for %r: %s", model_id, exc)
        return {"error": str(exc)}
