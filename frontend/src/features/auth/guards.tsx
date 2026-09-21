import { Navigate, Outlet, useLocation, useSearchParams } from "react-router";

import type { UserRole } from "../../api/types";
import { FullScreenLoader } from "../../shared/ui/FullScreenLoader";
import { StatusPage } from "../../shared/ui/StatusPage";
import { useAuth } from "./AuthContext";
import { loginPathFor, safeNext } from "./next";

export const CHANGE_PASSWORD_PATH = "/change-password";

export function RequireAuth() {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === "loading") return <FullScreenLoader />;
  if (state.status === "guest") {
    const to =
      state.reason === "logout" ? "/login" : loginPathFor(location.pathname, location.search);
    return <Navigate to={to} replace />;
  }
  if (state.user.must_change_password && location.pathname !== CHANGE_PASSWORD_PATH) {
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />;
  }
  return <Outlet />;
}

export function RequireRole({ role }: { role: UserRole }) {
  const { user } = useAuth();
  if (user?.role !== role) {
    return (
      <StatusPage
        code={403}
        title="Нет доступа"
        text="У вас нет прав для просмотра этой страницы."
      />
    );
  }
  return <Outlet />;
}

export function GuestOnly() {
  const { state } = useAuth();
  const [searchParams] = useSearchParams();

  if (state.status === "loading") return <FullScreenLoader />;
  if (state.status === "authenticated") {
    return <Navigate to={safeNext(searchParams.get("next"))} replace />;
  }
  return <Outlet />;
}
