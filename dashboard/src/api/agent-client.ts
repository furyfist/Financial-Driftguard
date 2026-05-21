/**
 * agent-client.ts — typed API client for all FinSight AI endpoints.
 * Separate from client.ts so agent/trust/report calls are clearly scoped.
 *
 * Endpoints covered:
 *   POST /agent/ask          — conversational query
 *   POST /agent/analyze      — autonomous model analysis
 *   POST /agent/report       — PDF report download
 *   GET  /agent/log          — agent decision audit log
 *   GET  /trust/{model_id}   — agent-to-agent trust score
 */

import axios from "axios"
import type { AgentResponse, AgentLogEntry, TrustScore } from "../types"

const BASE = "http://localhost:8000"

const api = axios.create({ baseURL: BASE })

// ── Conversational agent ───────────────────────────────────────────────────────

export const agentApi = {
  /**
   * Free-text query to the governance agent.
   * Used by the AgentView chat interface (risk officer persona).
   */
  ask: (query: string, modelId?: string): Promise<AgentResponse> =>
    api
      .post<AgentResponse>("/agent/ask", { query, model_id: modelId ?? null })
      .then(r => r.data),

  /**
   * Trigger autonomous drift analysis for a model.
   * Agent calls its tools internally and returns a structured recommendation.
   */
  analyze: (modelId: string): Promise<AgentResponse> =>
    api
      .post<AgentResponse>("/agent/analyze", { model_id: modelId })
      .then(r => r.data),

  /**
   * Fetch recent agent decisions from the audit log.
   */
  log: (modelId?: string, limit = 10): Promise<AgentLogEntry[]> => {
    const params: Record<string, string | number> = { limit }
    if (modelId) params.model_id = modelId
    return api.get<AgentLogEntry[]>("/agent/log", { params }).then(r => r.data)
  },
}

// ── Report generation ──────────────────────────────────────────────────────────

export const reportApi = {
  /**
   * Generate an SR 11-7 PDF and trigger a browser download.
   * Returns the blob URL so the caller can revoke it after use.
   * date_range format: "YYYY-MM-DD/YYYY-MM-DD" (empty → last 30 days)
   */
  generate: async (modelId: string, dateRange = ""): Promise<string> => {
    const response = await fetch(`${BASE}/agent/report`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ model_id: modelId, date_range: dateRange }),
    })
    if (!response.ok) {
      const detail = await response.text()
      throw new Error(`Report generation failed (${response.status}): ${detail}`)
    }
    const blob = await response.blob()
    return URL.createObjectURL(blob)
  },

  /**
   * Convenience helper: generate report and immediately trigger browser download.
   */
  download: async (modelId: string, dateRange = ""): Promise<void> => {
    const url = await reportApi.generate(modelId, dateRange)
    const a   = document.createElement("a")
    a.href    = url
    a.download = `${modelId}_governance_report.pdf`
    a.click()
    // Delay revoke so the download can start
    setTimeout(() => URL.revokeObjectURL(url), 5_000)
  },
}

// ── Trust API ──────────────────────────────────────────────────────────────────

export const trustApi = {
  /**
   * Fetch a deterministic trust score for a model — no LLM, instant response.
   * context: optional hint about intended use (used to enrich the reason string).
   */
  score: (modelId: string, context = ""): Promise<TrustScore> => {
    const params = context ? { context } : {}
    return api
      .get<TrustScore>(`/trust/${modelId}`, { params })
      .then(r => r.data)
  },
}
