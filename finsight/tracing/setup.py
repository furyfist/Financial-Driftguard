"""Phoenix tracing initialisation — register OTEL provider and patch DriftGuard internals."""

import logging
import os

logger = logging.getLogger(__name__)

_TRACING_INITIALIZED = False


def init_tracing(project_name: str = "finsight-ai") -> bool:
    """
    Connect to Phoenix and apply tracing decorators to DriftGuard class methods.

    Idempotent — safe to call multiple times.
    Returns True on success, False if Phoenix is unreachable (app continues untraced).
    """
    global _TRACING_INITIALIZED
    if _TRACING_INITIALIZED:
        return True

    try:
        from phoenix.otel import register
        register(
            project_name=project_name,
            endpoint=os.getenv(
                "PHOENIX_COLLECTOR_ENDPOINT",
                "http://localhost:6006",
            ),
            batch=True,
        )
        logger.info("Phoenix tracing connected — project: %s", project_name)
    except Exception as exc:
        logger.warning(
            "Phoenix tracing unavailable, running without observability: %s", exc
        )
        return False

    _apply_tracing_decorators()
    _TRACING_INITIALIZED = True
    return True


def _apply_tracing_decorators() -> None:
    """
    Monkey-patch DriftGuard class methods with tracing decorators.
    No DriftGuard source files are modified — instrumentation is applied here at runtime.
    """
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

    logger.debug(
        "Tracing applied to: Monitor.check, RegimeTagger.tag, "
        "BaseDetector.detect, MacroSignalFetcher.fetch"
    )
