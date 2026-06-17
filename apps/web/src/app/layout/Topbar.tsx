import { API_BASE_URL } from "../../api/client";

export function Topbar() {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Cycle 7</p>
        <h1>Frontend Research Dashboard</h1>
      </div>
      <div className="api-pill">API {API_BASE_URL}</div>
    </header>
  );
}
