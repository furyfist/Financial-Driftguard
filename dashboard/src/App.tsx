import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Overview } from "./pages/Overview"
import { ModelDetail } from "./pages/ModelDetail"
import { Settings }    from "./pages/Settings"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                    element={<Overview />} />
        <Route path="/models/:modelId"     element={<ModelDetail />} />
        <Route path="/settings"        element={<Settings />} />
      </Routes>
    </BrowserRouter>
  )
}