import { toDisplayError } from "../../api/errors";

export function ErrorState({ error }: { error: unknown }) {
  const display = toDisplayError(error);
  return (
    <div className="state-box error">
      <h3>{display.title}</h3>
      <p>{display.message}</p>
    </div>
  );
}
