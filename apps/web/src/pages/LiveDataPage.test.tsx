import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { liveCandles, liveDataState, liveEvents, moexPollSkipped } from "../test/fixtures";
import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { LiveDataPage } from "./LiveDataPage";

describe("LiveDataPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders read-only live data state, candles and events", async () => {
    mockFetch({
      "/api/live-data/state": liveDataState,
      "/api/live-data/candles?limit=20": liveCandles,
      "/api/live-data/events?limit=20": liveEvents,
    });

    renderRoute("/live-data", <LiveDataPage />);

    expect(await screen.findByText("Live Data")).toBeInTheDocument();
    expect(screen.getByText("Свечи")).toBeInTheDocument();
    expect(screen.getAllByText("MOEX:SiH6").length).toBeGreaterThan(0);
    expect(screen.getByText("CANDLE_CLOSED")).toBeInTheDocument();
  });

  it("runs demo replay through HTTP API only", async () => {
    const fetchMock = mockFetch({
      "/api/live-data/state": liveDataState,
      "/api/live-data/candles?limit=20": liveCandles,
      "/api/live-data/events?limit=20": liveEvents,
      "/api/live-data/replay-demo": {
        status: "saved",
        source: "DEMO_REPLAY",
        run_id: "run-1",
        read_only: true,
        allow_network: false,
        snapshots_count: 5,
        latest_snapshot: liveCandles.candles[0],
      },
      "/api/live-data/poll/moex-once": moexPollSkipped,
    });

    renderRoute("/live-data", <LiveDataPage />);
    await screen.findByText("Live Data");
    await userEvent.click(screen.getByRole("button", { name: "Demo replay" }));

    expect(await screen.findByText("saved")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/live-data/replay-demo",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
