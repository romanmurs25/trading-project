import { useQueries } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import type { ContinuousSeries, HealthResponse, Instrument, MarketDataState, MarketSession, ResearchRun } from "../api/types";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { MetricCard } from "../components/ui/MetricCard";

export function DashboardPage() {
  const [health, instruments, researchRuns, sessions, continuousSeries, liveData] = useQueries({
    queries: [
      { queryKey: ["health"], queryFn: () => apiGet<HealthResponse>("/health") },
      { queryKey: ["instruments"], queryFn: () => apiGet<Instrument[]>("/api/instruments") },
      { queryKey: ["research-runs"], queryFn: () => apiGet<ResearchRun[]>("/api/research/runs") },
      { queryKey: ["market-sessions"], queryFn: () => apiGet<MarketSession[]>("/api/market/sessions") },
      { queryKey: ["continuous-series"], queryFn: () => apiGet<ContinuousSeries[]>("/api/continuous-series") },
      { queryKey: ["live-data-state"], queryFn: () => apiGet<MarketDataState>("/api/live-data/state") },
    ],
  });

  const error = [health, instruments, researchRuns, sessions, continuousSeries, liveData].find((query) => query.error)?.error;
  if (error) {
    return <ErrorState error={error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Обзор</p>
        <h2>Панель исследований</h2>
      </div>
      <div className="metric-grid">
        <MetricCard label="Backend" value={health.data?.status ?? "loading"} tone="success" />
        <MetricCard label="Инструменты" value={instruments.data?.length ?? "—"} />
        <MetricCard label="Исследования" value={researchRuns.data?.length ?? "—"} />
        <MetricCard label="Сессии" value={sessions.data?.length ?? "—"} />
        <MetricCard label="Непрерывные серии" value={continuousSeries.data?.length ?? "—"} />
        <MetricCard label="Live-свечи" value={liveData.data?.latest_candles_count ?? "—"} />
      </div>
      <Card title="Safety posture">
        {health.isLoading ? (
          <LoadingState />
        ) : (
          <dl className="details-grid">
            <div>
              <dt>Trading mode</dt>
              <dd>{health.data?.trading_mode ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Live trading</dt>
              <dd>{health.data?.live_trading_enabled ? "включен" : "отключен"}</dd>
            </div>
            <div>
              <dt>Frontend</dt>
              <dd>Только HTTP API, без секретов</dd>
            </div>
          </dl>
        )}
      </Card>
    </div>
  );
}
