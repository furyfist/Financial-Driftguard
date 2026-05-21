"""SMTP email notifier adapter — stdlib smtplib only, no new dependencies."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText

from driftguard.notifications.base import BaseNotifier, NotificationPayload

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Send drift alerts by email via SMTP with STARTTLS."""

    name = "email"

    def __init__(
        self,
        to_addr: str,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_addr: str | None = None,
        severity_threshold: str = "high",
    ) -> None:
        # email doesn't use a webhook URL — pass empty string to satisfy BaseNotifier
        super().__init__("", severity_threshold)
        self.to_addr       = to_addr
        self.smtp_host     = smtp_host
        self.smtp_port     = smtp_port
        self.smtp_user     = smtp_user
        self.smtp_password = smtp_password
        self.from_addr     = from_addr or smtp_user

    def send(self, payload: NotificationPayload) -> None:
        if not self.smtp_host:
            raise ValueError("SMTP_HOST not configured")

        top3 = payload.top_features[:3]
        feature_lines = "\n".join(
            f"  • {f['feature']} — score {f['score']:.4f} ({f['severity']})"
            for f in top3
        ) or "  None"

        body = (
            f"FinSight AI Drift Alert\n"
            f"{'=' * 40}\n\n"
            f"Model:       {payload.model_id}\n"
            f"Severity:    {payload.overall_severity.upper()}\n"
            f"Drift Score: {payload.drift_score:.4f}\n"
            f"Regime:      {payload.regime} ({payload.regime_confidence:.0%} confidence)\n"
            f"Checked At:  {payload.checked_at[:19].replace('T', ' ')} UTC\n\n"
            f"Recommendation:\n{payload.recommendation or 'N/A'}\n\n"
            f"Top Drifted Features:\n{feature_lines}\n"
        )

        subject = f"FinSight AI Alert — {payload.model_id} [{payload.overall_severity.upper()}]"
        msg           = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"]    = self.from_addr
        msg["To"]      = self.to_addr

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_addr, [self.to_addr], msg.as_string())

        logger.info(
            "Email alert sent to %s for %s [%s]",
            self.to_addr, payload.model_id, payload.overall_severity,
        )


def email_notifier_from_env() -> EmailNotifier | None:
    """
    Construct an EmailNotifier from environment variables.
    Returns None if SMTP_HOST is unset.

    Required env vars: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO
    Optional env vars: SMTP_PORT (default 587)
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    if not smtp_host:
        return None
    return EmailNotifier(
        to_addr       =os.environ.get("ALERT_EMAIL_TO", ""),
        smtp_host     =smtp_host,
        smtp_port     =int(os.environ.get("SMTP_PORT", "587")),
        smtp_user     =os.environ.get("SMTP_USER", ""),
        smtp_password =os.environ.get("SMTP_PASSWORD", ""),
    )
