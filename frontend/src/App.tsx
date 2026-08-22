import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { ComparePage } from "./pages/ComparePage";
import { DashboardPage } from "./pages/DashboardPage";
import { ETFDetailPage } from "./pages/ETFDetailPage";
import { SensitivityPage } from "./pages/SensitivityPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/sensitivity" element={<SensitivityPage />} />
        <Route path="/etf/:symbol" element={<ETFDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
