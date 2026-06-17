import { ApiError } from "./errors";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function apiGet<TResponse>(path: string): Promise<TResponse> {
  return request<TResponse>(path, { method: "GET" });
}

export async function apiPost<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
  return request<TResponse>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function request<TResponse>(path: string, init: RequestInit): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(new URL(path, API_BASE_URL).toString(), init);
  } catch (error) {
    throw new ApiError("Network request failed", "network", undefined, error);
  }

  const text = await response.text();
  const payload = text ? parseJson(text, response.status) : null;

  if (!response.ok) {
    throw new ApiError(errorMessage(payload) ?? response.statusText, "http", response.status, payload);
  }

  return payload as TResponse;
}

function parseJson(text: string, status: number): unknown {
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new ApiError("Response is not valid JSON", "parse", status, error);
  }
}

function errorMessage(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return null;
  }
  const detail = (payload as { detail: unknown }).detail;
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}
