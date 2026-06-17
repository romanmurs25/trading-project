import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { researchRun } from "../test/fixtures";
import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { ResearchRunsPage } from "./ResearchRunsPage";

describe("ResearchRunsPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders research runs", async () => {
    mockFetch({ "/api/research/runs": [researchRun] });

    renderRoute("/research", <ResearchRunsPage />);

    expect(await screen.findByText("opening_range_breakout")).toBeInTheDocument();
    expect(screen.getByText("COMPLETED")).toBeInTheDocument();
  });
});
