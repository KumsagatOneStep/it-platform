import type { RouteObject } from "react-router";

import {
  ChangePasswordPage,
  GuestOnly,
  LoginPage,
  ProfilePage,
  RequireAuth,
  useAuth,
} from "../features/auth";
import { HomePage } from "../features/home";
import { BlankLayout } from "../layout/BlankLayout";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

function ChangePasswordRoute() {
  const { user } = useAuth();
  return user?.must_change_password ? (
    <BlankLayout>
      <ChangePasswordPage forced />
    </BlankLayout>
  ) : (
    <FullLayout>
      <ChangePasswordPage />
    </FullLayout>
  );
}

export const routes: RouteObject[] = [
  {
    element: <GuestOnly />,
    children: [
      { element: <BlankLayout />, children: [{ path: "/login", element: <LoginPage /> }] },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      { path: "/change-password", element: <ChangePasswordRoute /> },
      {
        element: <FullLayout />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
