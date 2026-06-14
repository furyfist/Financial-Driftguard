import { BrowserRouter, Routes, Route } from "react-router-dom"
import LandingPage     from "./pages/LandingPage"
import { Overview }   from "./pages/Overview"
import { ModelDetail } from "./pages/ModelDetail"
import { Settings }    from "./pages/Settings"
import { ExperimentView } from "./pages/ExperimentView"
import { AgentView }   from "./pages/AgentView"
import { ApprovalsView } from "./pages/ApprovalsView"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                    element={<LandingPage />} />
        <Route path="/dashboard"           element={<Overview />} />
        <Route path="/models/:modelId"     element={<ModelDetail />} />
        <Route path="/settings"            element={<Settings />} />
        <Route path="/experiments"         element={<ExperimentView />} />
        <Route path="/agent"               element={<AgentView />} />
        <Route path="/approvals"           element={<ApprovalsView />} />
      </Routes>
    </BrowserRouter>
  )
}
