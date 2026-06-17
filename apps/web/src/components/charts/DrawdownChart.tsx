import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { BacktestEquityPoint } from "../../api/types";
import { EmptyState } from "../ui/EmptyState";
import { parseDecimalStringForChart } from "./chartUtils";

export function DrawdownChart({ points }: { points: BacktestEquityPoint[] }) {
  if (points.length === 0) {
    return <EmptyState title="No drawdown data" message="Drawdown chart needs stored equity points." />;
  }

  const data = points.map((point) => ({
    ts: point.ts,
    drawdown: parseDecimalStringForChart(point.drawdown),
  }));

  return (
    <div className="chart-box" aria-label="Drawdown chart">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data}>
          <XAxis dataKey="ts" hide />
          <YAxis width={72} />
          <Tooltip />
          <Area type="monotone" dataKey="drawdown" stroke="#b42318" fill="#fecdca" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
