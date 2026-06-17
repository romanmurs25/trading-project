import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { instrument } from "../test/fixtures";
import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { InstrumentsPage } from "./InstrumentsPage";

describe("InstrumentsPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders table from mocked API", async () => {
    mockFetch({ "/api/instruments": [instrument] });

    renderRoute("/instruments", <InstrumentsPage />);

    expect(await screen.findByText("MOEX:SiH6")).toBeInTheDocument();
    expect(screen.getByText("SiH6")).toBeInTheDocument();
  });
});
