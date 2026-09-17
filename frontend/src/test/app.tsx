import { AuthProvider } from "../features/auth";
import { routes } from "../app/routes";
import { renderRoutes } from "./render";

/** Рендерит приложение целиком (все маршруты, AuthProvider) на пути `path`. */
export function renderApp(path: string) {
  return renderRoutes(routes, {
    initialEntries: [path],
    wrapper: (children) => <AuthProvider>{children}</AuthProvider>,
  });
}
