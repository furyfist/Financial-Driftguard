import { useEffect, useState, useCallback } from "react"
import { approvalsApi } from "../api/client"
import type { ApprovalItem } from "../types"

const ACTION_COLORS: Record<string, string> = {
  freeze: "bg-red-100 text-red-800",
  halt: "bg-red-100 text-red-800",
  retrain: "bg-yellow-100 text-yellow-800",
  escalate: "bg-orange-100 text-orange-800",
}

const STATUS_COLORS: Record<string, string> = {
  pending: "text-yellow-600",
  approved: "text-green-600",
  rejected: "text-red-600",
}

function ActionBadge({ action }: { action: string }) {
  const cls = ACTION_COLORS[action] ?? "bg-gray-100 text-gray-700"
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${cls}`}>
      {action}
    </span>
  )
}

export default function ApprovalQueue() {
  const [items, setItems] = useState<ApprovalItem[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await approvalsApi.list()
      setItems(data)
    } catch {
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  async function handleApprove(id: number) {
    setBusy(id)
    try {
      await approvalsApi.approve(id)
      await load()
    } finally {
      setBusy(null)
    }
  }

  async function handleReject(id: number) {
    setBusy(id)
    try {
      await approvalsApi.reject(id)
      await load()
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <div className="text-sm text-gray-500">Loading approvals…</div>
  if (!items.length) return <div className="text-sm text-gray-500">No approval requests.</div>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b text-left text-gray-500 text-xs uppercase">
            <th className="pb-2 pr-4">Model</th>
            <th className="pb-2 pr-4">Action</th>
            <th className="pb-2 pr-4">Regime</th>
            <th className="pb-2 pr-4">Confidence</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2 pr-4">Created</th>
            <th className="pb-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.id} className="border-b hover:bg-gray-50">
              <td className="py-2 pr-4 font-mono text-xs">{item.model_id}</td>
              <td className="py-2 pr-4">
                <ActionBadge action={item.action} />
              </td>
              <td className="py-2 pr-4 text-xs text-gray-600">{item.regime}</td>
              <td className="py-2 pr-4 text-xs">{(item.confidence * 100).toFixed(0)}%</td>
              <td className={`py-2 pr-4 text-xs font-semibold ${STATUS_COLORS[item.status] ?? ""}`}>
                {item.status.toUpperCase()}
              </td>
              <td className="py-2 pr-4 text-xs text-gray-500">
                {new Date(item.created_at).toLocaleString()}
              </td>
              <td className="py-2">
                {item.status === "pending" && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleApprove(item.id)}
                      disabled={busy === item.id}
                      className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(item.id)}
                      disabled={busy === item.id}
                      className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
                {item.status !== "pending" && (
                  <span className="text-xs text-gray-400">by {item.responded_by ?? "—"}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
