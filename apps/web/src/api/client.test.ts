import { afterEach, describe, expect, it, vi } from "vitest";

import { apiGet } from "./client";
import { ApiError } from "./errors";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("handles 200 response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ status: "ok" }), { status: 200 })));

    await expect(apiGet<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
  });

  it("handles non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "not found" }), { status: 404 })));

    await expect(apiGet("/missing")).rejects.toBeInstanceOf(ApiError);
  });
});
