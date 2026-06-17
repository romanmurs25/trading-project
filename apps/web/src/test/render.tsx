import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

export function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

export function renderRoute(path: string, element: ReactElement, initialEntry = path) {
  const router = createMemoryRouter([{ path, element }], {
    initialEntries: [initialEntry],
  });
  return renderWithProviders(<RouterProvider router={router} />);
}
