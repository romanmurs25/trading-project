import { Outlet } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Topbar />
        <div className="safety-banner">Read-only research dashboard. No live trading. No broker execution.</div>
        <main className="page-frame">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
