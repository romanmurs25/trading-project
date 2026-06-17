import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { apiGet } from "../api/client";
import type { Instrument } from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { Table } from "../components/ui/Table";

export function InstrumentsPage() {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const instruments = useQuery({
    queryKey: ["instruments"],
    queryFn: () => apiGet<Instrument[]>("/api/instruments"),
  });

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return instruments.data ?? [];
    }
    return (instruments.data ?? []).filter((instrument) =>
      [instrument.canonical_symbol, instrument.native_symbol, instrument.venue, instrument.asset_class]
        .join(" ")
        .toLowerCase()
        .includes(normalized),
    );
  }, [instruments.data, query]);

  if (instruments.isLoading) {
    return <LoadingState />;
  }
  if (instruments.error) {
    return <ErrorState error={instruments.error} />;
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Registry</p>
        <h2>Instruments</h2>
      </div>
      <Card>
        <input
          className="field"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by symbol, venue or asset class"
          aria-label="Search instruments"
        />
      </Card>
      {filtered.length === 0 ? (
        <EmptyState title="No instruments" message="Run MOEX instruments sync or adjust the filter." />
      ) : (
        <Table
          rows={filtered}
          getRowKey={(row) => row.id}
          onRowClick={(row) => navigate(`/instruments/${encodeURIComponent(row.id)}`)}
          columns={[
            { key: "canonical", header: "Canonical", render: (row) => row.canonical_symbol },
            { key: "native", header: "Native", render: (row) => row.native_symbol },
            { key: "asset", header: "Asset class", render: (row) => row.asset_class },
            { key: "venue", header: "Venue", render: (row) => row.venue },
            { key: "expiry", header: "Expiry", render: (row) => row.expiry_date ?? "—" },
            {
              key: "active",
              header: "Active",
              render: (row) => <Badge tone={row.is_active ? "success" : "neutral"}>{row.is_active ? "yes" : "no"}</Badge>,
            },
          ]}
        />
      )}
    </div>
  );
}
