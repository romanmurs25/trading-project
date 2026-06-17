import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { dataQualityReport } from "../test/fixtures";
import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { DataQualityPage } from "./DataQualityPage";

describe("DataQualityPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders session-aware report", async () => {
    mockFetch({ "/api/data/quality/session-aware?canonical_symbol=MOEX%3ASiH6&interval=1m&from=2026-01-01&to=2026-01-02": dataQualityReport });

    renderRoute("/data-quality", <DataQualityPage />);

    expect(await screen.findByText("missing expected session candles: 2")).toBeInTheDocument();
    expect(screen.getByText("Пропущено")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Вне сессий")).toBeInTheDocument();
    expect(screen.getByText("Сессии")).toBeInTheDocument();
    expect(screen.getByText("MAIN")).toBeInTheDocument();
    expect(screen.getByText("Ожидалось")).toBeInTheDocument();
  });
});
