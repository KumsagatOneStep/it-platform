import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SnackbarProvider } from "notistack";
import type { ReactElement, ReactNode } from "react";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";

import { theme } from "../theme/theme";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } },
  });
}

export function TestProviders({
  children,
  queryClient = createTestQueryClient(),
}: {
  children: ReactNode;
  queryClient?: QueryClient;
}) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <SnackbarProvider>{children}</SnackbarProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

interface RenderRoutesOptions {
  initialEntries?: string[];
  wrapper?: (children: ReactNode) => ReactNode;
}

/** Рендерит маршруты в memory-роутере со всеми провайдерами приложения. */
export function renderRoutes(routes: RouteObject[], options: RenderRoutesOptions = {}) {
  const router = createMemoryRouter(routes, { initialEntries: options.initialEntries ?? ["/"] });
  const user = userEvent.setup();
  const content = <RouterProvider router={router} />;
  const view = render(
    <TestProviders>{options.wrapper ? options.wrapper(content) : content}</TestProviders>,
  );
  return { ...view, router, user };
}

/** Рендерит один элемент на маршруте `path` (по умолчанию «*»). */
export function renderWithProviders(
  ui: ReactElement,
  options: RenderRoutesOptions & { path?: string } = {},
) {
  return renderRoutes([{ path: options.path ?? "*", element: ui }], options);
}
