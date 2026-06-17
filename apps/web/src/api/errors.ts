export type ApiErrorKind = "network" | "http" | "parse";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;
  readonly details?: unknown;

  constructor(message: string, kind: ApiErrorKind, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.details = details;
  }
}

export function toDisplayError(error: unknown): { title: string; message: string } {
  if (error instanceof ApiError) {
    const status = error.status ? `HTTP ${error.status}. ` : "";
    return { title: "API request failed", message: `${status}${error.message}` };
  }
  if (error instanceof Error) {
    return { title: "Unexpected error", message: error.message };
  }
  return { title: "Unexpected error", message: "Unknown error" };
}
