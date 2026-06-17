import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { apiGet } from "../api/client";
import type { ResearchRun } from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { DateTimeCell } from "../components/ui/DateTimeCell";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { Table } from "../components/ui/Table";

export function ResearchRunsPage() {
  const [filter, setFilter] = useState("");
  const navigate = useNavigate();
  const runs = useQuery({
    queryKey: ["research-runs"],
    queryFn: () => apiGet<ResearchRun[]>("/api/research/runs"),
  });
  const rows = useMemo(() => {
    const normalized = filter.trim().toLowerCase();
    if (!normalized) {
      return runs.data ?? [];
    }
    return (runs.data ?? []).filter((run) =>
      [run.strategy_id, run.canonical_symbol, run.status].join(" ").toLowerCase().includes(normalized),
    );
  }, [filter, runs.data]);

  if (runs.isLoading) {
    return <LoadingState />;
  }
  if (runs.error) {
    return <ErrorState error={runs.error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Research</p>
        <h2>Исследовательские прогоны</h2>
      </div>
      <Card>
        <input className="field" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Фильтр по стратегии, символу или статусу" />
      </Card>
      {rows.length === 0 ? (
        <EmptyState title="Прогонов нет" message="Запустите research workflow после загрузки свечей." />
      ) : (
        <Table
          rows={rows}
          getRowKey={(row) => row.id}
          onRowClick={(row) => navigate(`/research/${encodeURIComponent(row.id)}`)}
          columns={[
            { key: "id", header: "ID", render: (row) => row.id },
            { key: "strategy", header: "Стратегия", render: (row) => row.strategy_id },
            { key: "symbol", header: "Символ", render: (row) => row.canonical_symbol },
            { key: "interval", header: "Интервал", render: (row) => row.interval },
            { key: "period", header: "Период", render: (row) => `${row.start.slice(0, 10)} → ${row.end.slice(0, 10)}` },
            { key: "status", header: "Статус", render: (row) => <Badge tone={row.status === "COMPLETED" ? "success" : "warning"}>{row.status}</Badge> },
            { key: "created", header: "Создан", render: (row) => <DateTimeCell value={row.created_at} /> },
            { key: "completed", header: "Завершен", render: (row) => <DateTimeCell value={row.completed_at} /> },
          ]}
        />
      )}
    </div>
  );
}
