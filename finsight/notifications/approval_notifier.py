"""Approval notification builders — Slack Block Kit and Telegram inline keyboard."""

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _impact_estimate(confidence: float) -> str:
    if confidence >= 0.90:
        return "$3.2M–$4.8M exposure"
    if confidence >= 0.70:
        return "$1.2M–$2.4M exposure"
    return "< $1M exposure"


class SlackApprovalNotifier:
    """Send Slack Block Kit approval request messages."""

    def send(self, approval) -> bool:
        """
        Post a Slack message with Approve/Reject buttons for an ApprovalQueue entry.
        Returns True on success.
        """
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not set — skipping Slack approval notification")
            return False

        blocks = self._build_blocks(approval)
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(webhook_url, json={"blocks": blocks})
                resp.raise_for_status()
            logger.info("Slack approval notification sent for approval_id=%s", approval.id)
            return True
        except Exception as exc:
            logger.warning("Slack approval notification failed: %s", exc)
            return False

    def _build_blocks(self, approval) -> list:
        impact = _impact_estimate(approval.confidence)
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "FinSight AI — Action Requires Approval",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Model:*\n{approval.model_id}"},
                    {"type": "mrkdwn", "text": f"*Regime:*\n{approval.regime}"},
                    {"type": "mrkdwn", "text": f"*Action:*\n`{approval.action.upper()}`"},
                    {"type": "mrkdwn", "text": f"*Confidence:*\n{approval.confidence:.0%}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Estimated Impact:* {impact}\n\n*Recommendation:*\n{approval.recommendation[:400]}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "action_id": "approve_action",
                        "value": str(approval.id),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "action_id": "reject_action",
                        "value": str(approval.id),
                        "style": "danger",
                    },
                ],
            },
        ]


class TelegramApprovalNotifier:
    """Send Telegram inline keyboard approval request messages."""

    def send(self, approval) -> bool:
        """
        Post a Telegram message with Approve/Reject inline buttons.
        Returns True on success.
        """
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping Telegram approval")
            return False

        impact = _impact_estimate(approval.confidence)
        text = (
            f"FinSight AI — Action Requires Approval\n\n"
            f"Model: {approval.model_id}\n"
            f"Regime: {approval.regime}\n"
            f"Action: {approval.action.upper()}\n"
            f"Confidence: {approval.confidence:.0%}\n"
            f"Impact: {impact}\n\n"
            f"Recommendation: {approval.recommendation[:300]}"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Approve", "callback_data": f"approve_{approval.id}"},
                    {"text": "Reject", "callback_data": f"reject_{approval.id}"},
                ]
            ]
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "reply_markup": reply_markup,
                        "parse_mode": "Markdown",
                    },
                )
                resp.raise_for_status()
            logger.info("Telegram approval notification sent for approval_id=%s", approval.id)
            return True
        except Exception as exc:
            logger.warning("Telegram approval notification failed: %s", exc)
            return False


def send_approval_notification(approval) -> None:
    """Fire approval notifications on all configured channels. Best-effort."""
    SlackApprovalNotifier().send(approval)
    TelegramApprovalNotifier().send(approval)
