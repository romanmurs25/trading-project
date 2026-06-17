import { vi } from "vitest";

export function mockFetch(routes: Record<string, unknown>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    const key = `${url.pathname}${url.search}`;
    const withoutSearch = url.pathname;
    const payload = key in routes ? routes[key] : routes[withoutSearch];
    if (payload === undefined) {
      return new Response(JSON.stringify({ detail: `unhandled ${key}` }), { status: 404 });
    }
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
