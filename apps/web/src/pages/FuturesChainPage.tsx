import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import type { FrontContractResponse, FuturesChainResponse } from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { Table } from "../components/ui/Table";

export function FuturesChainPage() {
  const [form, setForm] = useState({ underlying: "Si", asOf: "2026-03-16", rollDays: "5" });
  const [submitted, setSubmitted] = useState(form);
  const params = new URLSearchParams({
    underlying: submitted.underlying,
  });
  const frontParams = new URLSearchParams({
    underlying: submitted.underlying,
    as_of: submitted.asOf,
    roll_days_before_expiry: submitted.rollDays,
  });
  const chain = useQuery({
    queryKey: ["futures-chain", submitted.underlying],
    queryFn: () => apiGet<FuturesChainResponse>(`/api/futures/chain?${params}`),
  });
  const front = useQuery({
    queryKey: ["futures-front", submitted],
    queryFn: () => apiGet<FrontContractResponse>(`/api/futures/select-front?${frontParams}`),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(form);
  }

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Контракты</p>
        <h2>Фьючерсная цепочка</h2>
      </div>
      <Card title="Выбор">
        <form className="form-grid" onSubmit={submit}>
          <label>
            Underlying
            <input className="field" value={form.underlying} onChange={(event) => setForm({ ...form, underlying: event.target.value })} />
          </label>
          <label>
            Дата
            <input className="field" type="date" value={form.asOf} onChange={(event) => setForm({ ...form, asOf: event.target.value })} />
          </label>
          <label>
            Roll days
            <input className="field" value={form.rollDays} onChange={(event) => setForm({ ...form, rollDays: event.target.value })} />
          </label>
          <Button type="submit">Обновить</Button>
        </form>
      </Card>
      {front.data ? (
        <Card title="Выбранный front contract">
          <dl className="details-grid">
            <div>
              <dt>Canonical symbol</dt>
              <dd>{front.data.selected_canonical_symbol}</dd>
            </div>
            <div>
              <dt>Причина</dt>
              <dd>{front.data.reason}</dd>
            </div>
            <div>
              <dt>Дней до экспирации</dt>
              <dd>{front.data.days_to_expiry}</dd>
            </div>
          </dl>
        </Card>
      ) : null}
      {chain.isLoading || front.isLoading ? <LoadingState /> : null}
      {chain.error ? <ErrorState error={chain.error} /> : null}
      {front.error ? <ErrorState error={front.error} /> : null}
      {chain.data?.contracts.length === 0 ? (
        <EmptyState title="Контрактов нет" message="Сначала сохраните MOEX futures instruments и contract specs." />
      ) : null}
      {chain.data && chain.data.contracts.length > 0 ? (
        <Table
          rows={chain.data.contracts}
          getRowKey={(row) => row.id}
          columns={[
            { key: "canonical", header: "Canonical", render: (row) => row.canonical_symbol },
            { key: "native", header: "Native", render: (row) => row.native_symbol },
            { key: "expiry", header: "Экспирация", render: (row) => row.expiry_date ?? "—" },
            { key: "active", header: "Активен", render: (row) => <Badge tone={row.is_active ? "success" : "neutral"}>{row.is_active ? "да" : "нет"}</Badge> },
          ]}
        />
      ) : null}
    </div>
  );
}
