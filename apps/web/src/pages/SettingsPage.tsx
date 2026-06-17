import { useQuery } from "@tanstack/react-query";

import { API_BASE_URL, apiGet } from "../api/client";
import type { HealthResponse } from "../api/types";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";

export function SettingsPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/health"),
  });

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Runtime</p>
        <h2>Settings</h2>
      </div>
      <Card title="API">
        <dl className="details-grid">
          <div>
            <dt>Base URL</dt>
            <dd>{API_BASE_URL}</dd>
          </div>
          <div>
            <dt>Configured by</dt>
            <dd>VITE_API_BASE_URL</dd>
          </div>
        </dl>
      </Card>
      <Card title="Backend health">
        {health.isLoading ? <LoadingState /> : null}
        {health.error ? <ErrorState error={health.error} /> : null}
        {health.data ? (
          <dl className="details-grid">
            <div>
              <dt>Status</dt>
              <dd>{health.data.status}</dd>
            </div>
            <div>
              <dt>Trading mode</dt>
              <dd>{health.data.trading_mode}</dd>
            </div>
            <div>
              <dt>Live trading</dt>
              <dd>{health.data.live_trading_enabled ? "enabled" : "disabled"}</dd>
            </div>
          </dl>
        ) : null}
      </Card>
      <Card title="Safety constraints">
        <ul className="plain-list">
          <li>No live trading controls.</li>
          <li>No broker execution.</li>
          <li>No secrets or broker tokens in frontend.</li>
          <li>No order placement UI.</li>
          <li>No live market data WebSocket.</li>
        </ul>
      </Card>
    </div>
  );
}
