import { ru } from "../../i18n/ru";

export function LoadingState({ label = ru.states.loading }: { label?: string }) {
  return <div className="state-box subtle">{label}</div>;
}
