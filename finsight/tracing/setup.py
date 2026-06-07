"""Phoenix tracing initialisation — register OTEL provider and instrument DriftGuard internals."""

import logging
import os

logger = logging.getLogger(__name__)

_TRACING_INITIALIZED = False


def init_tracing(project_name: str = "finsight-ai") -> bool:
    """
    Connect to Phoenix (local or Arize cloud) and instrument DriftGuard internals.
    Idempotent — safe to call multiple times.
    Returns True on success, False if Phoenix is unreachable (app continues untraced).
    """
    global _TRACING_INITIALIZED
    if _TRACING_INITIALIZED:
        return True

    tracer_provider = None

    try:
        from phoenix.otel import register

        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
        api_key = os.getenv("PHOENIX_API_KEY", "")

        headers = {}
        if api_key:
            headers["api_key"] = api_key

        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            headers=headers if headers else None,
            auto_instrument=True,
            batch=True,
        )
        logger.info("Phoenix tracing connected — project: %s endpoint: %s", project_name, endpoint)
    except Exception as exc:
        logger.warning("Phoenix tracing unavailable, running without observability: %s", exc)
        return False

    _apply_tracing_decorators()
    _TRACING_INITIALIZED = True
    return True


def _apply_tracing_decorators() -> None:
    """Monkey-patch DriftGuard class methods with tracing decorators."""
    try:
        from driftguard.core.monitor import Monitor
        from driftguard.regime.tagger import RegimeTagger
        from driftguard.detectors.base import BaseDetector
        from driftguard.regime.macro_signals import MacroSignalFetcher
        from .decorators import (
            traced_drift_check,
            traced_regime_tag,
            traced_detector,
            traced_macro_fetch,
        )

        Monitor.check = traced_drift_check(Monitor.check)
        RegimeTagger.tag = traced_regime_tag(RegimeTagger.tag)
        BaseDetector.detect = traced_detector(BaseDetector.detect)
        MacroSignalFetcher.fetch = traced_macro_fetch(MacroSignalFetcher.fetch)

        logger.debug("Tracing decorators applied to Monitor, RegimeTagger, BaseDetector, MacroSignalFetcher")
    except Exception as exc:
        logger.warning("Tracing decorators failed to apply: %s", exc)
