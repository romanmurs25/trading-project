import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "../api/client";
import type { SessionAwareQualityResponse } from "../api/types";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { MetricCard } from "../components/ui/MetricCard";

export function DataQualityPage() {
  const [form, setForm] = useState({
    canonicalSymbol: "MOEX:SiH6",
    interval: "1m",
    from: "2026-01-01",
    to: "2026-01-02",
    mode: "session-aware",
  });
  const [submitted, setSubmitted] = useState(form);
  const report = useQuery({
    queryKey: ["data-quality", submitted],
    queryFn: () =>
      apiGet<SessionAwareQualityResponse>(
        `/api/data/quality/session-aware?${new URLSearchParams({
          canonical_symbol: submitted.canonicalSymbol,
          interval: submitted.interval,
          from: submitted.from,
          to: submitted.to,
        })}`,
      ),
    enabled: submitted.mode === "session-aware",
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(form);
  }

  const data = report.data?.report;

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Свечи</p>
        <h2>Качество данных</h2>
      </div>
      <Card title="Проверка качества">
        <form className="form-grid" onSubmit={submit}>
          <label>
            Canonical symbol
            <input className="field" value={form.canonicalSymbol} onChange={(event) => setForm({ ...form, canonicalSymbol: event.target.value })} />
          </label>
          <label>
            Интервал
            <input className="field" value={form.interval} onChange={(event) => setForm({ ...form, interval: event.target.value })} />
          </label>
          <label>
            С
            <input className="field" type="date" value={form.from} onChange={(event) => setForm({ ...form, from: event.target.value })} />
          </label>
          <label>
            По
            <input className="field" type="date" value={form.to} onChange={(event) => setForm({ ...form, to: event.target.value })} />
          </label>
          <label>
            Режим
            <select className="field" value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>
              <option value="session-aware">session-aware</option>
              <option value="continuous-time" disabled>continuous-time placeholder</option>
            </select>
          </label>
          <Button type="submit">Проверить</Button>
        </form>
      </Card>
      {report.isLoading ? <LoadingState /> : null}
      {report.error ? <ErrorState error={report.error} /> : null}
      {data ? (
        <>
          <div className="metric-grid">
            <MetricCard label="Свечи" value={data.candles_count} />
            <MetricCard label="Ожидалось" value={data.expected_candles_count} />
            <MetricCard
              label="Пропущено"
              value={data.missing_expected_candles_count}
              tone={data.missing_expected_candles_count ? "warning" : "success"}
            />
            <MetricCard label="Дубликаты" value={data.duplicates_count} />
            <MetricCard label="Вне сессий" value={data.unexpected_out_of_session_count} />
            <MetricCard label="Порядок" value={data.non_monotonic_count} />
            <MetricCard label="Нулевой объём" value={data.zero_volume_count} />
          </div>
          <Card title="Сессии">
            <ul className="plain-list">
              {Object.entries(data.session_counts).map(([sessionType, count]) => (
                <li key={sessionType}>
                  <span className="mono">{sessionType}</span>: {count}
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Предупреждения">
            <ul className="plain-list">
              {(data.warnings.length ? data.warnings : ["предупреждений нет"]).map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </Card>
        </>
      ) : null}
    </div>
  );
}
