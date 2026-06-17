import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { frontContract, futuresChain } from "../test/fixtures";
import { renderRoute } from "../test/render";
import { mockFetch } from "../test/server";
import { FuturesChainPage } from "./FuturesChainPage";

describe("FuturesChainPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders selected contract", async () => {
    mockFetch({
      "/api/futures/chain?underlying=Si": futuresChain,
      "/api/futures/select-front?underlying=Si&as_of=2026-03-16&roll_days_before_expiry=5": frontContract,
    });

    renderRoute("/futures-chain", <FuturesChainPage />);

    expect(await screen.findByText("Selected front contract")).toBeInTheDocument();
    expect(screen.getAllByText("MOEX:SiH6").length).toBeGreaterThan(0);
  });
});
