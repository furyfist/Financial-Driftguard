"""Phoenix tracing initialisation — register OTEL provider and auto-instrument ADK."""

import logging
import os

logger = logging.getLogger(__name__)

_TRACING_INITIALIZED = False


def init_tracing(project_name: str = "finsight-ai") -> bool:
    """
    Connect to Phoenix and instrument ADK + DriftGuard internals.

    MUST be called before any google.adk imports (ADK instrumentor requirement).
    Idempotent — safe to call multiple times.
    Returns True on success, False if Phoenix is unreachable (app continues untraced).
    """
    global _TRACING_INITIALIZED
    if _TRACING_INITIALIZED:
        return True

    tracer_provider = None

    try:
        from phoenix.otel import register
        tracer_provider = register(
            project_name=project_name,
            endpoint=os.getenv(
                "PHOENIX_COLLECTOR_ENDPOINT",
                "http://localhost:6006/v1/traces",
            ),
            auto_instrument=True,
            batch=True,
        )
        logger.info("Phoenix tracing connected — project: %s", project_name)
    except Exception as exc:
        logger.warning("Phoenix tracing unavailable, running without observability: %s", exc)
        return False

    _try_instrument_adk(tracer_provider)
    _apply_tracing_decorators()
    _TRACING_INITIALIZED = True
    return True


def _try_instrument_adk(tracer_provider) -> None:
    """Register GoogleADKInstrumentor if the package is installed."""
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.debug("GoogleADKInstrumentor registered")
    except ImportError:
        logger.debug("openinference-instrumentation-google-adk not installed, skipping ADK auto-instrumentation")
    except Exception as exc:
        logger.warning("GoogleADKInstrumentor failed to register: %s", exc)


def _apply_tracing_decorators() -> None:
    """Monkey-patch DriftGuard class methods with tracing decorators."""
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
