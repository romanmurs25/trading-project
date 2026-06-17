import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { ContinuousSeriesPage } from "./ContinuousSeriesPage";

describe("ContinuousSeriesPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders empty state when no data", async () => {
    mockFetch({ "/api/continuous-series": [] });

    renderRoute("/continuous", <ContinuousSeriesPage />);

    expect(await screen.findByText("Серий нет")).toBeInTheDocument();
  });
});
