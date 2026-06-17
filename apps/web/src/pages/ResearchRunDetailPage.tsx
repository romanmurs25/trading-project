import { useQueries, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { apiGet } from "../api/client";
import type {
  ResearchBacktestResult,
  ResearchComparison,
  ResearchEquityResponse,
  ResearchRun,
  ResearchTradesResponse,
} from "../api/types";
import { DrawdownChart } from "../components/charts/DrawdownChart";
import { EquityCurveChart } from "../components/charts/EquityCurveChart";
import { MetricBarChart } from "../components/charts/MetricBarChart";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { DateTimeCell } from "../components/ui/DateTimeCell";
import { DecimalCell } from "../components/ui/DecimalCell";
import { ErrorState } from "../components/ui/ErrorState";
import { JsonBlock } from "../components/ui/JsonBlock";
import { LoadingState } from "../components/ui/LoadingState";
import { MetricCard } from "../components/ui/MetricCard";
import { Table } from "../components/ui/Table";

export function ResearchRunDetailPage() {
  const { runId = "" } = useParams();
  const run = useQuery({
    queryKey: ["research-run", runId],
    queryFn: () => apiGet<ResearchRun>(`/api/research/runs/${encodeURIComponent(runId)}`),
    enabled: Boolean(runId),
  });
  const [results, compare, equity, trades] = useQueries({
    queries: [
      {
        queryKey: ["research-results", runId],
        queryFn: () => apiGet<ResearchBacktestResult[]>(`/api/research/runs/${encodeURIComponent(runId)}/results`),
        enabled: Boolean(runId),
      },
      {
        queryKey: ["research-compare", runId],
        queryFn: () => apiGet<ResearchComparison>(`/api/research/runs/${encodeURIComponent(runId)}/compare`),
        enabled: Boolean(runId),
      },
      {
        queryKey: ["research-equity", runId],
        queryFn: () => apiGet<ResearchEquityResponse>(`/api/research/runs/${encodeURIComponent(runId)}/equity`),
        enabled: Boolean(runId),
      },
      {
        queryKey: ["research-trades", runId],
        queryFn: () => apiGet<ResearchTradesResponse>(`/api/research/runs/${encodeURIComponent(runId)}/trades`),
        enabled: Boolean(runId),
      },
    ],
  });

  const error = [run, results, compare, equity, trades].find((query) => query.error)?.error;
  if (run.isLoading) {
    return <LoadingState />;
  }
  if (error) {
    return <ErrorState error={error} />;
  }

  const bestMetrics = compare.data?.best_row && typeof compare.data.best_row === "object"
    ? (compare.data.best_row as { metrics?: Record<string, string | number | null> }).metrics
    : undefined;

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Прогон исследования</p>
        <h2>{run.data?.id}</h2>
      </div>
      <div className="metric-grid">
        <MetricCard label="Стратегия" value={run.data?.strategy_id ?? "—"} />
        <MetricCard label="Символ" value={run.data?.canonical_symbol ?? "—"} />
        <MetricCard label="Статус" value={run.data?.status ?? "—"} />
        <MetricCard label="Best profit factor" value={bestMetrics?.profit_factor ?? "—"} />
        <MetricCard label="Best expectancy" value={bestMetrics?.expectancy ?? "—"} />
      </div>
      <Card title="Сводка" action={<Link to={`/research/${encodeURIComponent(runId)}/report`}><Button variant="secondary">Отчёт</Button></Link>}>
        <dl className="details-grid">
          <div>
            <dt>Interval</dt>
            <dd>{run.data?.interval}</dd>
          </div>
          <div>
            <dt>Начало</dt>
            <dd><DateTimeCell value={run.data?.start} /></dd>
          </div>
          <div>
            <dt>Конец</dt>
            <dd><DateTimeCell value={run.data?.end} /></dd>
          </div>
          <div>
            <dt>Создан</dt>
            <dd><DateTimeCell value={run.data?.created_at} /></dd>
          </div>
        </dl>
      </Card>
      <Card title="Сетка параметров">
        <JsonBlock value={run.data?.parameter_grid ?? {}} />
      </Card>
      <Card title="Результаты">
        {results.isLoading ? <LoadingState /> : null}
        {results.data ? (
          <Table
            rows={results.data}
            getRowKey={(row) => row.id}
            columns={[
              { key: "params", header: "Params", render: (row) => <JsonBlock value={row.params} /> },
              { key: "pf", header: "Profit factor", render: (row) => <DecimalCell value={row.metrics.profit_factor} /> },
              { key: "expectancy", header: "Expectancy", render: (row) => <DecimalCell value={row.metrics.expectancy} /> },
              { key: "pnl", header: "Total PnL", render: (row) => <DecimalCell value={row.metrics.total_pnl} /> },
              { key: "dd", header: "Max drawdown", render: (row) => <DecimalCell value={row.metrics.max_drawdown} /> },
              { key: "trades", header: "Сделки", render: (row) => <DecimalCell value={row.metrics.trades_count} /> },
              { key: "status", header: "Статус", render: (row) => row.status },
              { key: "error", header: "Ошибка", render: (row) => row.error_message ?? "—" },
            ]}
          />
        ) : null}
      </Card>
      <div className="split-grid">
        <Card title="Equity curve">
          <EquityCurveChart points={equity.data?.points ?? []} />
        </Card>
        <Card title="Drawdown">
          <DrawdownChart points={equity.data?.points ?? []} />
        </Card>
        <Card title="Лучшие метрики">
          <MetricBarChart
            rows={[
              { label: "PF", value: bestMetrics?.profit_factor },
              { label: "Expect", value: bestMetrics?.expectancy },
              { label: "PnL", value: bestMetrics?.total_pnl },
              { label: "Trades", value: bestMetrics?.trades_count },
            ]}
          />
        </Card>
      </div>
      <Card title="Сделки">
        <Table
          rows={trades.data?.trades ?? []}
          getRowKey={(row) => row.id}
          columns={[
            { key: "symbol", header: "Инструмент", render: (row) => row.instrument_id },
            { key: "side", header: "Сторона", render: (row) => row.side },
            { key: "entry", header: "Вход", render: (row) => <DateTimeCell value={row.entry_ts} /> },
            { key: "exit", header: "Выход", render: (row) => <DateTimeCell value={row.exit_ts} /> },
            { key: "qty", header: "Qty", render: (row) => <DecimalCell value={row.qty} /> },
            { key: "gross", header: "Gross PnL", render: (row) => <DecimalCell value={row.gross_pnl} /> },
            { key: "net", header: "Net PnL", render: (row) => <DecimalCell value={row.net_pnl} /> },
            { key: "r", header: "R", render: (row) => <DecimalCell value={row.r_multiple} /> },
            { key: "reason", header: "Причина", render: (row) => row.reason ?? "—" },
          ]}
        />
      </Card>
    </div>
  );
}
