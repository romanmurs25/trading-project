export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return <div className="state-box subtle">{label}</div>;
}
