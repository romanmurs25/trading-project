export function DecimalCell({ value }: { value?: string | number | null }) {
  if (value === null || value === undefined || value === "") {
    return <span className="muted">—</span>;
  }
  return <span className="mono">{String(value)}</span>;
}
