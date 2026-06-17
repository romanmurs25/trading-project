import { Outlet } from "react-router-dom";

import { ru } from "../../i18n/ru";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Topbar />
        <div className="safety-banner">{ru.safetyBanner}</div>
        <main className="page-frame">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
