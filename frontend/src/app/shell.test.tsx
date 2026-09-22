import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../api/types";
import { AuthProvider, ProfilePage, RequireAuth } from "../features/auth";
import { HomePage } from "../features/home";
import { makeMe, mockSignedIn } from "../test/auth";
import { renderRoutes } from "../test/render";
import { server } from "../test/server";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

const routes = [
  {
    element: <RequireAuth />,
    children: [
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

function renderShell(path: string) {
  return renderRoutes(routes, {
    initialEntries: [path],
    wrapper: (children) => <AuthProvider>{children}</AuthProvider>,
  });
}

function mockDepartments(departments: Schemas["DepartmentRead"][] = []) {
  server.use(http.get("*/api/departments", () => HttpResponse.json(departments)));
}

test("администратор видит раздел «Администрирование» в меню", async () => {
  mockSignedIn(makeMe({ role: "admin" }));
  renderShell("/");

  const nav = await screen.findByRole("navigation", { name: "Основное меню" });
  expect(within(nav).getByRole("link", { name: "Пользователи" })).toHaveAttribute(
    "href",
    "/admin/users",
  );
  expect(within(nav).getByText("Администрирование")).toBeInTheDocument();
  expect(within(nav).getByRole("link", { name: "Выдать / принять" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Главная" })).toBeInTheDocument();
  expect(screen.getByText("Здравствуйте, Иванов Иван")).toBeInTheDocument();
});

test("сотрудник не видит раздел «Администрирование»", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  renderShell("/");

  const nav = await screen.findByRole("navigation", { name: "Основное меню" });
  expect(within(nav).getByRole("link", { name: "Главная" })).toBeInTheDocument();
  expect(within(nav).queryByText("Администрирование")).not.toBeInTheDocument();
});

test("раздел «Склад и техника»: реестр всем, выдача только администратору", async () => {
  mockSignedIn(makeMe({ role: "manager" }));
  renderShell("/");

  const nav = await screen.findByRole("navigation", { name: "Основное меню" });
  expect(within(nav).getByRole("link", { name: "Реестр техники" })).toHaveAttribute(
    "href",
    "/equipment/assets",
  );
  expect(within(nav).queryByRole("link", { name: "Выдать / принять" })).not.toBeInTheDocument();
});

test("неизвестный путь показывает страницу 404", async () => {
  mockSignedIn();
  renderShell("/nowhere");

  expect(await screen.findByRole("heading", { name: "Страница не найдена" })).toBeInTheDocument();
  // Заголовок ставится в эффекте после отрисовки — ждём его, а не проверяем сразу.
  await waitFor(() => expect(document.title).toBe("Страница не найдена — IT-платформа"));
});

test("профиль показывает данные пользователя и название отдела", async () => {
  mockSignedIn(makeMe({ role: "manager", department_id: 7, email: "m@company.ru" }));
  mockDepartments([{ id: 7, name: "Бухгалтерия", head_id: 1 }]);
  renderShell("/profile");

  const main = await screen.findByRole("main");
  expect(await within(main).findByText("Бухгалтерия")).toBeInTheDocument();
  expect(within(main).getByText("m@company.ru")).toBeInTheDocument();
  expect(within(main).getByText("Руководитель")).toBeInTheDocument();
});

test("меню пользователя: выход ведёт на страницу входа", async () => {
  mockSignedIn();
  server.use(http.post("*/api/auth/logout", () => new HttpResponse(null, { status: 204 })));
  const { user, router } = renderRoutes(
    [...routes, { path: "/login", element: <p>страница входа</p> }],
    { initialEntries: ["/"], wrapper: (children) => <AuthProvider>{children}</AuthProvider> },
  );

  await user.click(await screen.findByRole("button", { name: "Меню пользователя" }));
  await user.click(await screen.findByRole("menuitem", { name: "Выйти" }));

  expect(await screen.findByText("страница входа")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/login");
});
