import axios from "axios"
import type { Model, DriftRun, FeatureResult, Alert, ModelVersion } from "../types"
import type { MacroSnapshot, WebhookConfig, DriftForecast, ChallengerResult } from "../types"

const api = axios.create({ baseURL: "http://localhost:8000" })

export const modelsApi = {
  list: () => api.get<Model[]>("/models/").then(r => r.data),
  get:  (id: string) => api.get<Model>(`/models/${id}`).then(r => r.data),
  create: (model_id: string, description: string) =>
    api.post<Model>("/models/", { model_id, description }).then(r => r.data),
}

export const driftApi = {
  latest:  (id: string) => api.get<DriftRun>(`/drift/${id}/latest`).then(r => r.data),
  history: (id: string, version?: string) =>
    api.get<DriftRun[]>(`/drift/${id}/history`, { params: version ? { version } : {} }).then(r => r.data),
  features: (id: string, runId: number) =>
    api.get<FeatureResult[]>(`/drift/${id}/features/${runId}`).then(r => r.data),
}

export const versionsApi = {
  list:    (modelId: string) =>
    api.get<ModelVersion[]>(`/models/${modelId}/versions`).then(r => r.data),
  create:  (modelId: string, version_label: string, description?: string) =>
    api.post<ModelVersion>(`/models/${modelId}/versions`, { version_label, description }).then(r => r.data),
  promote: (modelId: string, versionLabel: string) =>
    api.post<ModelVersion>(`/models/${modelId}/versions/${versionLabel}/promote`).then(r => r.data),
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

export const forecastApi = {
  get: (modelId: string) =>
    api.get<DriftForecast>(`/drift/forecast/${modelId}`).then(r => r.data),
}

export const experimentsApi = {
  trigger: (modelId: string) =>
    api.post<ChallengerResult>(`/experiments/${modelId}/challenger`).then(r => r.data),
  results: (modelId: string) =>
    api.get<ChallengerResult>(`/experiments/${modelId}/results`).then(r => r.data),
}

export const featureMetaApi = {
  get: () => api.get<Record<string, string>>("/drift/feature-meta").then(r => r.data),
}

export const approvalsApi = {
  list: (status?: string) =>
    api.get("/approvals", { params: status ? { status } : {} }).then(r => r.data),
  approve: (id: number) =>
    api.post(`/approvals/${id}/approve`).then(r => r.data),
  reject: (id: number) =>
    api.post(`/approvals/${id}/reject`).then(r => r.data),
}