import json
import urllib.request

from .base import BaseNotifier, NotificationPayload


class SlackNotifier(BaseNotifier):
    """
    Sends drift alerts to a Slack channel via webhook.
    Uses Slack Block Kit for structured formatting.

    Setup:
        1. api.slack.com/apps → Create App → Incoming Webhooks
        2. Activate → Add to workspace → copy Webhook URL
        3. Set SLACK_WEBHOOK_URL in .env
    """

    name = "slack"

    def send(self, payload: NotificationPayload):
        sev_emoji = self._severity_emoji(payload.overall_severity)
        reg_emoji = self._regime_emoji(payload.regime)

        feature_text = "\n".join([
            f"• `{f['feature']}` — {f['score']:.4f} ({f['severity']})"
            for f in payload.top_features[:3]
        ]) or "No features drifted"

        # Estimated impact — best-effort; omitted if finsight not installed.
        impact_text: str | None = None
        try:
            from finsight.impact.estimator import estimate_impact
            est = estimate_impact(payload.drift_score, payload.regime)
            if est.low_usd >= 1.0:
                impact_text = (
                    f"${est.low_usd / 1e6:.1f}M–${est.high_usd / 1e6:.1f}M "
                    f"(FNR +{est.fnr_increase_pct:.0f}%)"
                )
        except ImportError:
            pass

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{sev_emoji} Drift Alert — {payload.model_id}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity*\n`{payload.overall_severity.upper()}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Drift score*\n`{payload.drift_score:.4f}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Regime* {reg_emoji}\n`{payload.regime}` ({payload.regime_confidence:.0%})",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Checked at*\n{payload.checked_at[:19].replace('T', ' ')} UTC",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top drifted features*\n{feature_text}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Agent recommendation*\n{payload.recommendation[:300]}",
                },
            },
        ]

        if impact_text:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Estimated impact:* {impact_text}",
                    }
                ],
            })

        body = json.dumps({"blocks": blocks}).encode("utf-8")
        req  = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"Slack returned status {resp.status}")