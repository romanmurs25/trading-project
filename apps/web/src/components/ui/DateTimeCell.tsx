export function DateTimeCell({ value }: { value?: string | null }) {
  if (!value) {
    return <span className="muted">—</span>;
  }
  return <time dateTime={value}>{new Date(value).toLocaleString()}</time>;
}
