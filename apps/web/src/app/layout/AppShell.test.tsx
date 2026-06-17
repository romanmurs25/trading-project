import { screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("renders safety banner", () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <AppShell />,
        children: [{ index: true, element: <div>Dashboard content</div> }],
      },
    ]);

    renderWithProviders(<RouterProvider router={router} />);

    expect(
      screen.getByText("Только чтение: исследование и рыночные данные. Live trading и broker execution отключены."),
    ).toBeInTheDocument();
  });
});
