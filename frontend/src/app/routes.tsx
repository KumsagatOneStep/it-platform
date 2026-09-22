import { Navigate, type RouteObject } from "react-router";

import {
  ChangePasswordPage,
  GuestOnly,
  LoginPage,
  ProfilePage,
  RequireAuth,
  RequireRole,
  useAuth,
} from "../features/auth";
import { AssetPage, AssetsPage, IssuePage } from "../features/assets";
import { DepartmentsPage } from "../features/departments";
import { DirectoriesPage } from "../features/directories";
import { HomePage } from "../features/home";
import { MovementsPage } from "../features/movements";
import { StockItemPage, StockPage } from "../features/stock";
import { UsersPage } from "../features/users";
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
          { path: "/equipment", element: <Navigate to="/equipment/assets" replace /> },
          { path: "/equipment/assets", element: <AssetsPage /> },
          { path: "/equipment/assets/:id", element: <AssetPage /> },
          {
            element: <RequireRole role="admin" />,
            children: [
              { path: "/equipment/stock", element: <StockPage /> },
              { path: "/equipment/stock/:id", element: <StockItemPage /> },
              { path: "/equipment/movements", element: <MovementsPage /> },
              { path: "/equipment/issue", element: <IssuePage /> },
              { path: "/admin/users", element: <UsersPage /> },
              { path: "/admin/departments", element: <DepartmentsPage /> },
              {
                path: "/admin/directories",
                element: <Navigate to="/admin/directories/locations" replace />,
              },
              { path: "/admin/directories/:kind", element: <DirectoriesPage /> },
            ],
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
