import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../api/types";
import { renderApp } from "../test/app";
import { makeMe, mockSignedOut, mockSignedIn, tokenResponse } from "../test/auth";
import { errorBody } from "../test/http";
import { server } from "../test/server";

test("вход: успешный вход ведёт на исходную страницу", async () => {
  mockSignedOut();
  server.use(http.get("*/api/departments", () => HttpResponse.json([])));
  server.use(
    http.post("*/api/auth/login", () => HttpResponse.json(tokenResponse("t-login"))),
    http.get("*/api/auth/me", ({ request }) =>
      request.headers.get("Authorization") === "Bearer t-login"
        ? HttpResponse.json(makeMe({ full_name: "Сидоров Сидор" }))
        : HttpResponse.json(errorBody("unauthorized", "Требуется вход"), { status: 401 }),
    ),
  );
  const { user, router } = renderApp("/profile");

  await user.type(await screen.findByLabelText("Email"), "admin@company.ru");
  await user.type(screen.getByLabelText("Пароль"), "secret");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(await screen.findByText("Сидоров Сидор", { selector: "p" })).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/profile");
});

test("вход: неверный пароль и блокировка показывают сообщение backend", async () => {
  mockSignedOut();
  server.use(
    http.post("*/api/auth/login", () =>
      HttpResponse.json(errorBody("invalid_credentials", "Неверный email или пароль"), {
        status: 401,
      }),
    ),
  );
  const { user } = renderApp("/login");

  await user.click(await screen.findByRole("button", { name: "Войти" }));
  expect(await screen.findByText("Введите email")).toBeInTheDocument();

  await user.type(screen.getByLabelText("Email"), "admin@company.ru");
  await user.type(screen.getByLabelText("Пароль"), "wrong");
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Неверный email или пароль");

  server.use(
    http.post("*/api/auth/login", () =>
      HttpResponse.json(
        errorBody("login_locked", "Слишком много попыток входа, попробуйте позже"),
        {
          status: 429,
        },
      ),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Слишком много попыток входа");
});

test("обязательная смена пароля: форма без меню, после смены — главная", async () => {
  mockSignedIn(makeMe({ must_change_password: true }));
  server.use(
    http.post("*/api/auth/change-password", async ({ request }) => {
      const body = (await request.json()) as Schemas["ChangePasswordRequest"];
      if (body.current_password !== "temp") {
        return HttpResponse.json(
          errorBody("invalid_current_password", "Текущий пароль указан неверно"),
          {
            status: 422,
          },
        );
      }
      server.use(http.get("*/api/auth/me", () => HttpResponse.json(makeMe())));
      return HttpResponse.json(tokenResponse("t-new"));
    }),
  );
  const { user, router } = renderApp("/");

  expect(await screen.findByText(/Администратор выдал вам временный пароль/)).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Основное меню" })).not.toBeInTheDocument();

  await user.type(screen.getByLabelText("Текущий пароль"), "wrong");
  await user.type(screen.getByLabelText("Новый пароль"), "N3w-password!");
  await user.type(screen.getByLabelText("Повторите новый пароль"), "other");
  await user.click(screen.getByRole("button", { name: "Сменить пароль" }));
  expect(await screen.findByText("Пароли не совпадают")).toBeInTheDocument();

  await user.clear(screen.getByLabelText("Повторите новый пароль"));
  await user.type(screen.getByLabelText("Повторите новый пароль"), "N3w-password!");
  await user.click(screen.getByRole("button", { name: "Сменить пароль" }));
  expect(await screen.findByText("Текущий пароль указан неверно")).toBeInTheDocument();

  await user.clear(screen.getByLabelText("Текущий пароль"));
  await user.type(screen.getByLabelText("Текущий пароль"), "temp");
  await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

  expect(await screen.findByRole("heading", { name: "Главная" })).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/");
});

test("неизвестный путь внутри приложения показывает 404 в каркасе", async () => {
  mockSignedIn();
  renderApp("/nowhere");

  expect(await screen.findByRole("heading", { name: "Страница не найдена" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Основное меню" })).toBeInTheDocument();
});
