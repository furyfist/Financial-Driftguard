import json
import urllib.request

from .base import BaseNotifier, NotificationPayload


class TelegramNotifier(BaseNotifier):
    """
    Sends drift alerts to a Telegram chat via Bot API.
    Uses MarkdownV2 formatting.

    Setup:
        1. Message @BotFather on Telegram → /newbot → get token
        2. Add bot to your channel/group
        3. Get chat_id: https://api.telegram.org/bot<TOKEN>/getUpdates
        4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """

    name = "telegram"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        severity_threshold: str = "high",
    ):
        # Telegram uses token+chat_id, not a single webhook URL
        super().__init__(
            webhook_url=f"https://api.telegram.org/bot{bot_token}/sendMessage",
            severity_threshold=severity_threshold,
        )
        self.chat_id = chat_id

    def send(self, payload: NotificationPayload):
        sev_emoji = self._severity_emoji(payload.overall_severity)
        reg_emoji = self._regime_emoji(payload.regime)

        def esc(text: str) -> str:
            """Escape special chars for MarkdownV2."""
            for ch in r"_*[]()~`>#+-=|{}.!":
                text = text.replace(ch, f"\\{ch}")
            return text

        feature_lines = "\n".join([
            f"  • `{f['feature']}` — {f['score']:.4f} \\({f['severity']}\\)"
            for f in payload.top_features[:3]
        ]) or "  No features drifted"

        text = (
            f"{sev_emoji} *Drift Alert — {esc(payload.model_id)}*\n\n"
            f"*Severity:* `{payload.overall_severity.upper()}`\n"
            f"*Score:* `{payload.drift_score:.4f}`\n"
            f"*Regime:* `{esc(payload.regime)}` {reg_emoji} "
            f"\\({payload.regime_confidence:.0%} conf\\)\n\n"
            f"*Top drifted features:*\n{feature_lines}\n\n"
            f"*Recommendation:*\n_{esc(payload.recommendation[:200])}_\n\n"
            f"_DriftGuard v0\\.2\\.0 • "
            f"{esc(payload.checked_at[:19].replace('T', ' '))} UTC_"
        )

        body = json.dumps({
            "chat_id":    self.chat_id,
            "text":       text,
            "parse_mode": "MarkdownV2",
        }).encode("utf-8")

        req = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Telegram returned status {resp.status}")