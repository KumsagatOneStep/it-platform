import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useLocation } from "react-router";

import { makeMe, mockSignedIn, mockSignedOut } from "../../test/auth";
import { renderRoutes } from "../../test/render";
import { server } from "../../test/server";
import { useAuth } from "./AuthContext";
import { AUTH_CHANNEL, AuthProvider } from "./AuthProvider";
import { GuestOnly, RequireAuth, RequireRole } from "./guards";
import { safeNext } from "./next";

function Where() {
  const location = useLocation();
  const { user, logout } = useAuth();
  return (
    <>
      <p>
        путь: {location.pathname}
        {location.search}
      </p>
      <p>пользователь: {user?.full_name ?? "гость"}</p>
      <button onClick={() => void logout()}>Выйти</button>
    </>
  );
}

const routes = [
  { element: <GuestOnly />, children: [{ path: "/login", element: <Where /> }] },
  {
    element: <RequireAuth />,
    children: [
      { path: "/", element: <Where /> },
      { path: "/change-password", element: <Where /> },
      {
        element: <RequireRole role="admin" />,
        children: [{ path: "/admin/users", element: <Where /> }],
      },
    ],
  },
];

function renderApp(path: string) {
  return renderRoutes(routes, {
    initialEntries: [path],
    wrapper: (children) => <AuthProvider>{children}</AuthProvider>,
  });
}

test("гость перенаправляется на вход с возвратом на исходную страницу", async () => {
  mockSignedOut();
  renderApp("/admin/users?q=1");

  expect(await screen.findByText("путь: /login?next=%2Fadmin%2Fusers%3Fq%3D1")).toBeInTheDocument();
});

test("действующая refresh-cookie восстанавливает сессию", async () => {
  mockSignedIn(makeMe({ full_name: "Петров Пётр" }));
  renderApp("/admin/users");

  expect(await screen.findByText("пользователь: Петров Пётр")).toBeInTheDocument();
  expect(screen.getByText("путь: /admin/users")).toBeInTheDocument();
});

test("вошедший пользователь со страницы входа уходит на next", async () => {
  mockSignedIn();
  renderApp("/login?next=%2Fadmin%2Fusers");

  expect(await screen.findByText("путь: /admin/users")).toBeInTheDocument();
});

test("не-admin видит «Нет доступа» в админке", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  renderApp("/admin/users");

  expect(await screen.findByRole("heading", { name: "Нет доступа" })).toBeInTheDocument();
});

test("must_change_password отправляет на смену пароля", async () => {
  mockSignedIn(makeMe({ must_change_password: true }));
  renderApp("/");

  expect(await screen.findByText("путь: /change-password")).toBeInTheDocument();
});

test("выход очищает сессию и сообщает другим вкладкам", async () => {
  mockSignedIn();
  const logoutCalls: string[] = [];
  server.use(
    http.post("*/api/auth/logout", () => {
      logoutCalls.push("logout");
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const otherTab = new BroadcastChannel(AUTH_CHANNEL);
  const received = new Promise((resolve) => (otherTab.onmessage = (e) => resolve(e.data)));
  const { user } = renderApp("/");

  await user.click(await screen.findByRole("button", { name: "Выйти" }));

  expect(await screen.findByText("путь: /login")).toBeInTheDocument();
  await expect(received).resolves.toBe("logout");
  expect(logoutCalls).toHaveLength(1);
  otherTab.close();
});

test("выход в другой вкладке завершает сессию в этой", async () => {
  mockSignedIn();
  renderApp("/");
  await screen.findByText("пользователь: Иванов Иван");

  const otherTab = new BroadcastChannel(AUTH_CHANNEL);
  otherTab.postMessage("logout");
  otherTab.close();

  await waitFor(() => expect(screen.getByText("пользователь: гость")).toBeInTheDocument());
});

test("выход в другой вкладке приводит на /login без next", async () => {
  mockSignedIn();
  renderApp("/admin/users");
  await screen.findByText("пользователь: Иванов Иван");

  const otherTab = new BroadcastChannel(AUTH_CHANNEL);
  otherTab.postMessage("logout");
  otherTab.close();

  expect(await screen.findByText("путь: /login")).toBeInTheDocument();
});

test("safeNext пропускает только относительные пути", () => {
  expect(safeNext("/admin/users?q=1")).toBe("/admin/users?q=1");
  expect(safeNext("//evil.example")).toBe("/");
  expect(safeNext("https://evil.example")).toBe("/");
  expect(safeNext(null)).toBe("/");
});
