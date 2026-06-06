import ApprovalQueue from "../components/ApprovalQueue"

export function ApprovalsView() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Human Approval Gate</h1>
          <p className="mt-1 text-sm text-gray-600">
            High-risk agent actions (HALT, retrain, freeze, escalate) require explicit approval before execution.
            Approve or reject via this dashboard, Slack, or Telegram.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Approval Requests</h2>
            <span className="text-xs text-gray-400">Auto-refreshes every 5s</span>
          </div>
          <ApprovalQueue />
        </div>

        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
          <strong>How it works:</strong> When the FinSight AI agent recommends a high-impact action,
          it pauses and creates an entry here. The same request is also sent to Slack and Telegram
          with interactive Approve/Reject buttons. No action executes until explicitly approved.
        </div>
      </div>
    </div>
  )
}
