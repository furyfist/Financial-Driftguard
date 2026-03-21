import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { webhookApi } from "../api/client"
import type { WebhookConfig } from "../types"

export function Settings() {
  const navigate  = useNavigate()
  const [form, setForm] = useState<WebhookConfig>({
    platform:           "discord",
    webhook_url:        "",
    model_id:           null,
    severity_threshold: "high",
  })
  const [status, setStatus]   = useState<"idle" | "success" | "error">("idle")
  const [message, setMessage] = useState("")

  const handleSubmit = async () => {
    if (!form.webhook_url.startsWith("http")) {
      setStatus("error")
      setMessage("Webhook URL must start with https://")
      return
    }
    try {
      const result = await webhookApi.configure({
        ...form,
        model_id: form.model_id === "" ? null : form.model_id,
      })
      setStatus("success")
      setMessage(`Configured ${result.configured} for ${result.model_id} (threshold: ${result.threshold})`)
    } catch {
      setStatus("error")
      setMessage("Failed to configure webhook — check the URL and try again")
    }
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-surface border-b border-border px-8 py-4 flex items-center gap-4 sticky top-0 z-10">
        <button
          onClick={() => navigate("/")}
          className="text-ink-faint hover:text-ink font-mono text-sm transition-colors"
        >
          ← back
        </button>
        <div className="w-px h-4 bg-border" />
        <span className="font-display font-semibold text-ink">Notification settings</span>
      </header>

      <main className="max-w-2xl mx-auto px-8 py-8">
        <div className="mb-8">
          <h1 className="font-display font-semibold text-2xl text-ink tracking-tight">
            Webhook configuration
          </h1>
          <p className="text-ink-muted text-sm mt-1">
            Configure alerts for Discord or Slack when drift is detected.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-lg p-6 space-y-5">

          <div>
            <label className="block text-xs font-mono text-ink-muted mb-2">Platform</label>
            <div className="flex gap-3">
              {(["discord", "slack"] as const).map(p => (
                <button
                  key={p}
                  onClick={() => setForm(f => ({ ...f, platform: p }))}
                  className={`px-4 py-2 rounded-lg border text-sm font-mono transition-all ${
                    form.platform === p
                      ? "border-ink bg-ink text-canvas"
                      : "border-border text-ink-muted hover:border-ink-muted"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-ink-muted mb-2">
              Webhook URL
            </label>
            <input
              type="url"
              value={form.webhook_url}
              onChange={e => setForm(f => ({ ...f, webhook_url: e.target.value }))}
              placeholder={
                form.platform === "discord"
                  ? "https://discord.com/api/webhooks/..."
                  : "https://hooks.slack.com/services/..."
              }
              className="w-full px-3 py-2 border border-border rounded-lg font-mono text-sm bg-canvas focus:outline-none focus:border-ink"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-ink-muted mb-2">
              Model ID <span className="text-ink-faint">(leave blank for all models)</span>
            </label>
            <input
              type="text"
              value={form.model_id ?? ""}
              onChange={e => setForm(f => ({ ...f, model_id: e.target.value || null }))}
              placeholder="lending_club_v1"
              className="w-full px-3 py-2 border border-border rounded-lg font-mono text-sm bg-canvas focus:outline-none focus:border-ink"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-ink-muted mb-2">
              Severity threshold
            </label>
            <div className="flex gap-3">
              {(["low", "medium", "high", "critical"] as const).map(s => (
                <button
                  key={s}
                  onClick={() => setForm(f => ({ ...f, severity_threshold: s }))}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                    form.severity_threshold === s
                      ? "border-ink bg-ink text-canvas"
                      : "border-border text-ink-muted hover:border-ink-muted"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {status !== "idle" && (
            <div className={`px-4 py-3 rounded-lg text-sm font-mono ${
              status === "success"
                ? "bg-stable-soft text-stable border border-stable/20"
                : "bg-critical-soft text-critical border border-critical/20"
            }`}>
              {message}
            </div>
          )}

          <button
            onClick={handleSubmit}
            className="w-full py-2.5 bg-ink text-canvas rounded-lg font-mono text-sm hover:opacity-90 transition-opacity"
          >
            Configure webhook
          </button>
        </div>

        <div className="mt-6 bg-surface border border-border rounded-lg p-5">
          <h3 className="font-display font-medium text-sm text-ink mb-3">Setup guides</h3>
          <div className="space-y-3 text-xs font-mono text-ink-muted">
            <div>
              <span className="text-ink font-medium">Discord:</span>
              {" "}Channel settings → Integrations → Webhooks → New Webhook → Copy URL
            </div>
            <div>
              <span className="text-ink font-medium">Slack:</span>
              {" "}api.slack.com/apps → Create App → Incoming Webhooks → Add to workspace
            </div>
            <div>
              <span className="text-ink font-medium">Telegram:</span>
              {" "}Use the API directly — message @BotFather to create a bot token
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}