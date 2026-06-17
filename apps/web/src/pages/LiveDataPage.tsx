import { useMemo, useState } from "react";
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiPost } from "../api/client";
import type {
  DemoReplayResponse,
  LiveCandlesResponse,
  MarketDataEventsResponse,
  MarketDataState,
  MoexPollOnceResponse,
} from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { DateTimeCell } from "../components/ui/DateTimeCell";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { MetricCard } from "../components/ui/MetricCard";
import { Table } from "../components/ui/Table";

type LastAction = DemoReplayResponse | MoexPollOnceResponse | null;

export function LiveDataPage() {
  const queryClient = useQueryClient();
  const [lastAction, setLastAction] = useState<LastAction>(null);
  const [state, candles, events] = useQueries({
    queries: [
      { queryKey: ["live-data-state"], queryFn: () => apiGet<MarketDataState>("/api/live-data/state") },
      { queryKey: ["live-data-candles"], queryFn: () => apiGet<LiveCandlesResponse>("/api/live-data/candles?limit=20") },
      { queryKey: ["live-data-events"], queryFn: () => apiGet<MarketDataEventsResponse>("/api/live-data/events?limit=20") },
    ],
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["live-data-state"] });
    await queryClient.invalidateQueries({ queryKey: ["live-data-candles"] });
    await queryClient.invalidateQueries({ queryKey: ["live-data-events"] });
  };

  const replayDemo = useMutation({
    mutationFn: () =>
      apiPost<Record<string, unknown>, DemoReplayResponse>("/api/live-data/replay-demo", {
        canonical_symbol: "MOEX:SiH6",
        interval: "1m",
        count: 5,
      }),
    onSuccess: async (response) => {
      setLastAction(response);
      await refresh();
    },
  });

  const pollMoexNoNetwork = useMutation({
    mutationFn: () =>
      apiPost<Record<string, unknown>, MoexPollOnceResponse>("/api/live-data/poll/moex-once", {
        symbol: "SiH6",
        instrument_id: "moex:SiH6",
        interval: "1m",
        allow_network: false,
      }),
    onSuccess: async (response) => {
      setLastAction(response);
      await refresh();
    },
  });

  const error = [state, candles, events].find((query) => query.error)?.error ?? replayDemo.error ?? pollMoexNoNetwork.error;
  const isLoading = [state, candles, events].some((query) => query.isLoading);
  const latestCandles = candles.data?.candles ?? [];
  const marketEvents = events.data?.events ?? [];
  const sourcesText = useMemo(() => (state.data?.sources.length ? state.data.sources.join(", ") : "—"), [state.data]);

  if (isLoading) {
    return <LoadingState />;
  }
  if (error) {
    return <ErrorState error={error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Read-only market data</p>
        <h2>Live Data</h2>
      </div>

      <div className="metric-grid">
        <MetricCard label="Статус ingestion" value={state.data?.status ?? "UNKNOWN"} tone={state.data?.status === "RUNNING" ? "success" : "neutral"} />
        <MetricCard label="Свечи" value={state.data?.latest_candles_count ?? 0} />
        <MetricCard label="Stale свечи" value={state.data?.stale_candles_count ?? 0} tone={state.data?.stale_candles_count ? "warning" : "success"} />
        <MetricCard label="Источники" value={sourcesText} />
      </div>

      <Card title="Операции только чтения">
        <div className="action-row">
          <Button type="button" onClick={() => replayDemo.mutate()} disabled={replayDemo.isPending}>
            Demo replay
          </Button>
          <Button type="button" variant="secondary" onClick={() => pollMoexNoNetwork.mutate()} disabled={pollMoexNoNetwork.isPending}>
            MOEX poll без сети
          </Button>
          {lastAction ? <Badge tone={lastAction.status === "skipped" ? "warning" : "success"}>{lastAction.status}</Badge> : null}
        </div>
      </Card>

      {state.data?.warnings.length ? (
        <Card title="Предупреждения">
          <ul className="plain-list">
            {state.data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      {latestCandles.length === 0 ? (
        <EmptyState title="Нет live-свечей" message="Demo replay создаёт безопасные offline-свечи." />
      ) : (
        <Card title="Последние свечи">
          <Table
            rows={latestCandles}
            getRowKey={(row) => row.id}
            columns={[
              { key: "symbol", header: "Символ", render: (row) => row.canonical_symbol },
              { key: "interval", header: "Интервал", render: (row) => row.interval },
              { key: "close", header: "Close", render: (row) => row.close },
              { key: "volume", header: "Объём", render: (row) => row.volume },
              { key: "freshness", header: "Freshness", render: (row) => <Badge tone={row.freshness === "FRESH" ? "success" : "warning"}>{row.freshness}</Badge> },
              { key: "updated", header: "Обновлено", render: (row) => <DateTimeCell value={row.updated_at} /> },
            ]}
          />
        </Card>
      )}

      {marketEvents.length === 0 ? null : (
        <Card title="События ingestion">
          <Table
            rows={marketEvents}
            getRowKey={(row) => row.id}
            columns={[
              { key: "event", header: "Событие", render: (row) => row.event_type },
              { key: "source", header: "Источник", render: (row) => row.source },
              { key: "symbol", header: "Символ", render: (row) => row.canonical_symbol },
              { key: "received", header: "Получено", render: (row) => <DateTimeCell value={row.received_at} /> },
            ]}
          />
        </Card>
      )}
    </div>
  );
}
