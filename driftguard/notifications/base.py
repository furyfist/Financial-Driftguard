from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """
    Unified notification payload — all adapters receive this.
    Constructed from a DriftResult + RegimeAssessment.
    """
    model_id:         str
    overall_severity: str
    drift_score:      float
    regime:           str
    regime_confidence: float
    recommendation:   str
    top_features:     list[dict]   # [{"feature": str, "score": float, "severity": str}]
    checked_at:       str          # ISO format


class BaseNotifier(ABC):
    """
    Abstract base for all notification adapters.
    Subclasses implement send() for their platform.
    """

    name: str = "base"

    def __init__(self, webhook_url: str, severity_threshold: str = "high"):
        self.webhook_url        = webhook_url
        self.severity_threshold = severity_threshold
        self._order = ["none", "low", "medium", "high", "critical"]

    def should_notify(self, severity: str) -> bool:
        """Only notify if severity meets or exceeds threshold."""
        try:
            return (
                self._order.index(severity) >=
                self._order.index(self.severity_threshold)
            )
        except ValueError:
            return False

    def notify(self, payload: NotificationPayload) -> bool:
        """
        Public entry point. Checks threshold then calls send().
        Returns True if notification was sent.
        """
        if not self.should_notify(payload.overall_severity):
            logger.debug(
                f"[{self.name}] Skipping — severity {payload.overall_severity} "
                f"below threshold {self.severity_threshold}"
            )
            return False

        try:
            self.send(payload)
            logger.info(
                f"[{self.name}] Notification sent for '{payload.model_id}' "
                f"— {payload.overall_severity} | {payload.regime}"
            )
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Notification failed: {e}")
            return False

    @abstractmethod
    def send(self, payload: NotificationPayload):
        """Platform-specific send implementation."""
        ...

    @staticmethod
    def _severity_emoji(severity: str) -> str:
        return {
            "critical": "🔴",
            "high":     "🟠",
            "medium":   "🟡",
            "low":      "🟢",
            "none":     "⚪",
        }.get(severity, "⚪")

    @staticmethod
    def _regime_emoji(regime: str) -> str:
        return {
            "black_swan":   "🦢",
            "recession":    "📉",
            "credit_stress":"⚠️",
            "rate_shock":   "📈",
            "stable":       "✅",
            "unknown":      "❓",
        }.get(regime, "❓")