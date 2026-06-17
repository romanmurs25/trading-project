import { API_BASE_URL } from "../../api/client";
import { ru } from "../../i18n/ru";

export function Topbar() {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">{ru.appCycle}</p>
        <h1>{ru.appTitle}</h1>
      </div>
      <div className="api-pill">API {API_BASE_URL}</div>
    </header>
  );
}
