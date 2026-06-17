import { useQueries } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import type { ContinuousSeries, HealthResponse, Instrument, MarketSession, ResearchRun } from "../api/types";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { MetricCard } from "../components/ui/MetricCard";

export function DashboardPage() {
  const [health, instruments, researchRuns, sessions, continuousSeries] = useQueries({
    queries: [
      { queryKey: ["health"], queryFn: () => apiGet<HealthResponse>("/health") },
      { queryKey: ["instruments"], queryFn: () => apiGet<Instrument[]>("/api/instruments") },
      { queryKey: ["research-runs"], queryFn: () => apiGet<ResearchRun[]>("/api/research/runs") },
      { queryKey: ["market-sessions"], queryFn: () => apiGet<MarketSession[]>("/api/market/sessions") },
      { queryKey: ["continuous-series"], queryFn: () => apiGet<ContinuousSeries[]>("/api/continuous-series") },
    ],
  });

  const error = [health, instruments, researchRuns, sessions, continuousSeries].find((query) => query.error)?.error;
  if (error) {
    return <ErrorState error={error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Research overview</p>
        <h2>Dashboard</h2>
      </div>
      <div className="metric-grid">
        <MetricCard label="Backend health" value={health.data?.status ?? "loading"} tone="success" />
        <MetricCard label="Instruments" value={instruments.data?.length ?? "—"} />
        <MetricCard label="Research runs" value={researchRuns.data?.length ?? "—"} />
        <MetricCard label="Market sessions" value={sessions.data?.length ?? "—"} />
        <MetricCard label="Continuous series" value={continuousSeries.data?.length ?? "—"} />
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
              <dt>Live trading enabled</dt>
              <dd>{health.data?.live_trading_enabled ? "true" : "false"}</dd>
            </div>
            <div>
              <dt>Frontend mode</dt>
              <dd>Read-only HTTP dashboard</dd>
            </div>
          </dl>
        )}
      </Card>
    </div>
  );
}
