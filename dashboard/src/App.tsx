import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Overview }        from "./pages/Overview"
import { ModelDetail }     from "./pages/ModelDetail"
import { Settings }        from "./pages/Settings"
import { ExperimentView }  from "./pages/ExperimentView"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                element={<Overview />} />
        <Route path="/models/:modelId" element={<ModelDetail />} />
        <Route path="/settings"        element={<Settings />} />
        <Route path="/experiments"     element={<ExperimentView />} />
      </Routes>
    </BrowserRouter>
  )
}