import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { SnackbarProvider } from "notistack";
import type { ReactNode } from "react";

import { AuthProvider } from "../features/auth";
import { theme } from "../theme/theme";

export function AppProviders({
  queryClient,
  children,
}: {
  queryClient: QueryClient;
  children: ReactNode;
}) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: "bottom", horizontal: "right" }}>
          <AuthProvider>{children}</AuthProvider>
        </SnackbarProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
