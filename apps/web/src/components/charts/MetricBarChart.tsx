import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "../ui/EmptyState";
import { parseDecimalStringForChart } from "./chartUtils";

interface MetricRow {
  label: string;
  value: string | number | null | undefined;
}

export function MetricBarChart({ rows }: { rows: MetricRow[] }) {
  if (rows.length === 0) {
    return <EmptyState title="No metric rows" message="Result metrics will appear after research runs are stored." />;
  }

  const data = rows.map((row) => ({
    label: row.label,
    value: parseDecimalStringForChart(row.value),
  }));

  return (
    <div className="chart-box" aria-label="Metric bar chart">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data}>
          <XAxis dataKey="label" />
          <YAxis width={72} />
          <Tooltip />
          <Bar dataKey="value" fill="#287c6f" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
