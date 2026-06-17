import { useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import type { ContinuousSeries, ContinuousSeriesComponentsResponse, RollEvent } from "../api/types";
import { Card } from "../components/ui/Card";
import { DateTimeCell } from "../components/ui/DateTimeCell";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { JsonBlock } from "../components/ui/JsonBlock";
import { LoadingState } from "../components/ui/LoadingState";
import { Table } from "../components/ui/Table";

export function ContinuousSeriesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const series = useQuery({
    queryKey: ["continuous-series"],
    queryFn: () => apiGet<ContinuousSeries[]>("/api/continuous-series"),
  });
  const selected = series.data?.find((item) => item.id === selectedId) ?? series.data?.[0] ?? null;
  const [components, rollEvents] = useQueries({
    queries: [
      {
        queryKey: ["continuous-components", selected?.id],
        queryFn: () => apiGet<ContinuousSeriesComponentsResponse>(`/api/continuous-series/${selected?.id}/components`),
        enabled: Boolean(selected?.id),
      },
      {
        queryKey: ["roll-events", selected?.underlying_symbol],
        queryFn: () => apiGet<RollEvent[]>(`/api/roll-events?${new URLSearchParams({ underlying_symbol: selected?.underlying_symbol ?? "" })}`),
        enabled: Boolean(selected?.underlying_symbol),
      },
    ],
  });

  if (series.isLoading) {
    return <LoadingState />;
  }
  if (series.error) {
    return <ErrorState error={series.error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Continuous futures</p>
        <h2>Continuous Series</h2>
      </div>
      {series.data?.length === 0 ? (
        <EmptyState title="No continuous series" message="Build one from CLI: trading data build-continuous --underlying Si --interval 1m --from 2026-03-13 --to 2026-03-17 --write" />
      ) : null}
      {series.data && series.data.length > 0 ? (
        <Table
          rows={series.data}
          getRowKey={(row) => row.id}
          onRowClick={(row) => setSelectedId(row.id)}
          columns={[
            { key: "canonical", header: "Canonical", render: (row) => row.canonical_symbol },
            { key: "underlying", header: "Underlying", render: (row) => row.underlying_symbol },
            { key: "interval", header: "Interval", render: (row) => row.interval },
            { key: "method", header: "Adjustment", render: (row) => row.adjustment_method },
            { key: "start", header: "Start", render: (row) => <DateTimeCell value={row.start} /> },
            { key: "end", header: "End", render: (row) => <DateTimeCell value={row.end} /> },
          ]}
        />
      ) : null}
      {selected ? (
        <div className="split-grid">
          <Card title={`Components: ${selected.canonical_symbol}`}>
            {components.isLoading ? <LoadingState /> : null}
            {components.error ? <ErrorState error={components.error} /> : null}
            {components.data ? (
              <Table
                rows={components.data.components}
                getRowKey={(row) => row.id}
                columns={[
                  { key: "symbol", header: "Symbol", render: (row) => row.canonical_symbol },
                  { key: "instrument", header: "Instrument ID", render: (row) => row.instrument_id },
                  { key: "start", header: "Start", render: (row) => <DateTimeCell value={row.start} /> },
                  { key: "end", header: "End", render: (row) => <DateTimeCell value={row.end} /> },
                ]}
              />
            ) : null}
          </Card>
          <Card title="Roll events">
            {rollEvents.data ? (
              <Table
                rows={rollEvents.data}
                getRowKey={(row) => row.id}
                columns={[
                  { key: "date", header: "Date", render: (row) => row.roll_date },
                  { key: "from", header: "From", render: (row) => row.from_instrument_id },
                  { key: "to", header: "To", render: (row) => row.to_instrument_id },
                  { key: "reason", header: "Reason", render: (row) => row.reason },
                ]}
              />
            ) : null}
          </Card>
          <Card title="Metadata">
            <JsonBlock value={selected.metadata} />
          </Card>
        </div>
      ) : null}
    </div>
  );
}
