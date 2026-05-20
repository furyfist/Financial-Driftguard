"""Phoenix observability layer — structured tracing for every DriftGuard operation."""

from .setup import init_tracing
from .decorators import (
    traced_drift_check,
    traced_regime_tag,
    traced_detector,
    traced_macro_fetch,
)

__all__ = [
    "init_tracing",
    "traced_drift_check",
    "traced_regime_tag",
    "traced_detector",
    "traced_macro_fetch",
]
