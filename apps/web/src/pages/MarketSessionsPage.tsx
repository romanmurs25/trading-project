import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import type { MarketSession } from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { DateTimeCell } from "../components/ui/DateTimeCell";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { Table } from "../components/ui/Table";

export function MarketSessionsPage() {
  const [venue, setVenue] = useState("MOEX");
  const [market, setMarket] = useState("forts");
  const sessions = useQuery({
    queryKey: ["market-sessions", venue, market],
    queryFn: () =>
      apiGet<MarketSession[]>(
        `/api/market/sessions?${new URLSearchParams({ venue, market })}`,
      ),
  });
  const rows = useMemo(() => sessions.data ?? [], [sessions.data]);

  if (sessions.isLoading) {
    return <LoadingState />;
  }
  if (sessions.error) {
    return <ErrorState error={sessions.error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">MOEX</p>
        <h2>Рыночные сессии</h2>
      </div>
      <Card>
        <div className="filter-row">
          <input className="field" value={venue} onChange={(event) => setVenue(event.target.value)} aria-label="Venue" />
          <input className="field" value={market} onChange={(event) => setMarket(event.target.value)} aria-label="Market" />
        </div>
      </Card>
      {rows.length === 0 ? (
        <EmptyState title="Сессий нет" message="Сгенерируйте сессии через CLI/API перед сохранением." />
      ) : (
        <Table
          rows={rows}
          getRowKey={(row) => row.id}
          columns={[
            { key: "date", header: "Дата", render: (row) => row.session_date },
            { key: "type", header: "Тип", render: (row) => row.session_type },
            { key: "start", header: "Начало", render: (row) => <DateTimeCell value={row.start} /> },
            { key: "end", header: "Конец", render: (row) => <DateTimeCell value={row.end} /> },
            { key: "trading", header: "Торговая", render: (row) => <Badge tone={row.is_trading ? "success" : "neutral"}>{row.is_trading ? "да" : "нет"}</Badge> },
            { key: "tz", header: "Часовой пояс", render: (row) => row.timezone },
          ]}
        />
      )}
    </div>
  );
}
