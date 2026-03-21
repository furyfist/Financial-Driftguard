import json
import urllib.request
from datetime import datetime

from .base import BaseNotifier, NotificationPayload


class DiscordNotifier(BaseNotifier):
    """
    Sends drift alerts to a Discord channel via webhook.
    Creates a rich embed with severity colour coding.

    Setup:
        1. Discord server → channel settings → Integrations → Webhooks
        2. Create webhook → copy URL
        3. Set DISCORD_WEBHOOK_URL in .env
    """

    name = "discord"

    # Embed colours per severity — Discord uses decimal colours
    _COLOURS = {
        "critical": 0xC0200F,   # red
        "high":     0xD4450C,   # orange
        "medium":   0xB45309,   # amber
        "low":      0x1A6B3C,   # green
        "none":     0x6B6860,   # grey
    }

    def send(self, payload: NotificationPayload):
        sev_emoji   = self._severity_emoji(payload.overall_severity)
        reg_emoji   = self._regime_emoji(payload.regime)
        colour      = self._COLOURS.get(payload.overall_severity, 0x6B6860)

        # Top 3 drifted features as field value
        feature_lines = "\n".join([
            f"`{f['feature']}` — PSI {f['score']:.4f} ({f['severity']})"
            for f in payload.top_features[:3]
        ]) or "No features drifted"

        embed = {
            "title": f"{sev_emoji} Drift Alert — {payload.model_id}",
            "color": colour,
            "fields": [
                {
                    "name":   "Severity",
                    "value":  f"`{payload.overall_severity.upper()}`",
                    "inline": True,
                },
                {
                    "name":   "Drift score",
                    "value":  f"`{payload.drift_score:.4f}`",
                    "inline": True,
                },
                {
                    "name":   f"Regime {reg_emoji}",
                    "value":  f"`{payload.regime}` ({payload.regime_confidence:.0%})",
                    "inline": True,
                },
                {
                    "name":   "Top drifted features",
                    "value":  feature_lines,
                    "inline": False,
                },
                {
                    "name":   "Recommendation",
                    "value":  payload.recommendation[:1024],
                    "inline": False,
                },
            ],
            "footer": {
                "text": f"DriftGuard v0.2.0 • {payload.checked_at[:19].replace('T', ' ')} UTC"
            },
            "timestamp": payload.checked_at,
        }

        body = json.dumps({"embeds": [embed]}).encode("utf-8")
        req  = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(
                    f"Discord returned status {resp.status}"
                )