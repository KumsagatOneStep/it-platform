import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";

import { AppProviders } from "./providers";
import { createQueryClient } from "./queryClient";
import { routes } from "./routes";

export function App() {
  const [queryClient] = useState(createQueryClient);
  const [router] = useState(() => createBrowserRouter(routes));
  return (
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
