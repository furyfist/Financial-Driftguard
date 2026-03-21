import axios from "axios"
import type { Model, DriftRun, FeatureResult, Alert } from "../types"
import type { MacroSnapshot, WebhookConfig } from "../types"

const api = axios.create({ baseURL: "http://localhost:8000" })

export const modelsApi = {
  list: () => api.get<Model[]>("/models/").then(r => r.data),
  get:  (id: string) => api.get<Model>(`/models/${id}`).then(r => r.data),
  create: (model_id: string, description: string) =>
    api.post<Model>("/models/", { model_id, description }).then(r => r.data),
}

export const driftApi = {
  latest:  (id: string) => api.get<DriftRun>(`/drift/${id}/latest`).then(r => r.data),
  history: (id: string) => api.get<DriftRun[]>(`/drift/${id}/history`).then(r => r.data),
  features: (id: string, runId: number) =>
    api.get<FeatureResult[]>(`/drift/${id}/features/${runId}`).then(r => r.data),
}

export const alertsApi = {
  list: (unackOnly = false) =>
    api.get<Alert[]>(`/alerts/?unacknowledged_only=${unackOnly}`).then(r => r.data),
  forModel: (id: string) => api.get<Alert[]>(`/alerts/${id}`).then(r => r.data),
  acknowledge: (alertId: number) =>
    api.post("/alerts/acknowledge", { alert_id: alertId }).then(r => r.data),
}

export const macroApi = {
  latest: () => api.get<MacroSnapshot>("/drift/macro/latest").then(r => r.data),
}

export const webhookApi = {
  configure: (config: WebhookConfig) =>
    api.post("/alerts/webhooks/configure", config).then(r => r.data),
}