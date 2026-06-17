import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "./layout/AppShell";
import { ContinuousSeriesPage } from "../pages/ContinuousSeriesPage";
import { DashboardPage } from "../pages/DashboardPage";
import { DataQualityPage } from "../pages/DataQualityPage";
import { FuturesChainPage } from "../pages/FuturesChainPage";
import { InstrumentDetailPage } from "../pages/InstrumentDetailPage";
import { InstrumentsPage } from "../pages/InstrumentsPage";
import { MarketSessionsPage } from "../pages/MarketSessionsPage";
import { ResearchReportPage } from "../pages/ResearchReportPage";
import { ResearchRunDetailPage } from "../pages/ResearchRunDetailPage";
import { ResearchRunsPage } from "../pages/ResearchRunsPage";
import { SettingsPage } from "../pages/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "instruments", element: <InstrumentsPage /> },
      { path: "instruments/:instrumentId", element: <InstrumentDetailPage /> },
      { path: "instruments/by-symbol/:canonicalSymbol", element: <InstrumentDetailPage /> },
      { path: "data-quality", element: <DataQualityPage /> },
      { path: "sessions", element: <MarketSessionsPage /> },
      { path: "futures-chain", element: <FuturesChainPage /> },
      { path: "continuous", element: <ContinuousSeriesPage /> },
      { path: "research", element: <ResearchRunsPage /> },
      { path: "research/:runId", element: <ResearchRunDetailPage /> },
      { path: "research/:runId/report", element: <ResearchReportPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);
