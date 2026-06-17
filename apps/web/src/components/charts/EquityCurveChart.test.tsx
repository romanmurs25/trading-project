import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { EquityCurveChart } from "./EquityCurveChart";

describe("EquityCurveChart", () => {
  it("handles empty data", () => {
    renderWithProviders(<EquityCurveChart points={[]} />);

    expect(screen.getByText("No equity points")).toBeInTheDocument();
  });
});
