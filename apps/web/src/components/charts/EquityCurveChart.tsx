import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { BacktestEquityPoint } from "../../api/types";
import { EmptyState } from "../ui/EmptyState";
import { parseDecimalStringForChart } from "./chartUtils";

export function EquityCurveChart({ points }: { points: BacktestEquityPoint[] }) {
  if (points.length === 0) {
    return <EmptyState title="No equity points" message="Equity curve will appear after a stored backtest run." />;
  }

  const data = points.map((point) => ({
    ts: point.ts,
    equity: parseDecimalStringForChart(point.equity),
    backtest: point.backtest_run_id,
  }));

  return (
    <div className="chart-box" aria-label="Equity curve chart">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <XAxis dataKey="ts" hide />
          <YAxis domain={["auto", "auto"]} width={72} />
          <Tooltip />
          <Line type="monotone" dataKey="equity" stroke="#176b87" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
