interface MetricCardProps {
  label: string;
  value: string | number;
  tone?: "neutral" | "success" | "warning" | "danger";
}

export function MetricCard({ label, value, tone = "neutral" }: MetricCardProps) {
  return (
    <div className={`metric-card metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
