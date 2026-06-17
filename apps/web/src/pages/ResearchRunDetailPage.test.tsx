import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { researchComparison, researchEquity, researchResult, researchRun, researchTrades } from "../test/fixtures";
import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { ResearchRunDetailPage } from "./ResearchRunDetailPage";

describe("ResearchRunDetailPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders result metrics", async () => {
    mockFetch({
      "/api/research/runs/research-1": researchRun,
      "/api/research/runs/research-1/results": [researchResult],
      "/api/research/runs/research-1/compare": researchComparison,
      "/api/research/runs/research-1/equity": researchEquity,
      "/api/research/runs/research-1/trades": researchTrades,
    });

    renderRoute("/research/:runId", <ResearchRunDetailPage />, "/research/research-1");

    expect(await screen.findByText("Best profit factor")).toBeInTheDocument();
    expect(screen.getAllByText("1.5").length).toBeGreaterThan(0);
    expect(screen.getByText("paper closed trade")).toBeInTheDocument();
  });
});
