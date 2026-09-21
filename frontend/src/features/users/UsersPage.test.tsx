import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../../api/types";
import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeUser, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";

const DEPARTMENTS: Schemas["DepartmentRead"][] = [{ id: 3, name: "Бухгалтерия", head_id: null }];

function mockUsers(users: Schemas["UserRead"][], seen: URL[] = []) {
  server.use(
    http.get("*/api/departments", () => HttpResponse.json(DEPARTMENTS)),
    http.get("*/api/admin/users", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(page(users));
    }),
  );
  return seen;
}

async function openRowMenu(user: ReturnType<typeof renderApp>["user"], fullName: string) {
  const row = (await screen.findByText(fullName)).closest("tr")!;
  await user.click(within(row).getByRole("button", { name: "Действия" }));
}

test("список пользователей с фильтрами из URL", async () => {
  mockSignedIn();
  const seen = mockUsers([makeUser({ department_id: 3, must_change_password: true })]);
  const { user, router } = renderApp("/admin/users?role=employee");

  const row = (await screen.findByText("Петров Пётр")).closest("tr")!;
  expect(within(row).getByText("Бухгалтерия")).toBeInTheDocument();
  expect(within(row).getByText("Временный пароль")).toBeInTheDocument();
  expect(seen.at(-1)?.searchParams.get("role")).toBe("employee");

  await user.type(screen.getByLabelText("Поиск по ФИО и email"), "пет");
  await waitFor(() => expect(seen.at(-1)?.searchParams.get("q")).toBe("пет"));
  expect(router.state.location.search).toContain("q=");
});

test("создание пользователя показывает временный пароль", async () => {
  mockSignedIn();
  mockUsers([]);
  let created: Schemas["UserCreate"] | null = null;
  server.use(
    http.post("*/api/admin/users", async ({ request }) => {
      created = (await request.json()) as Schemas["UserCreate"];
      return HttpResponse.json<Schemas["UserCreatedResponse"]>(
        { user: makeUser({ full_name: created.full_name }), temporary_password: "Tmp-12345" },
        { status: 201 },
      );
    }),
  );
  const { user } = renderApp("/admin/users");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("ФИО"), "Сидоров Сидор");
  await user.type(within(dialog).getByLabelText("Email"), "sidorov@company.ru");
  await user.click(within(dialog).getByLabelText("Отдел"));
  await user.click(await screen.findByRole("option", { name: "Бухгалтерия" }));
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  expect(await screen.findByDisplayValue("Tmp-12345")).toBeInTheDocument();
  expect(created).toEqual({
    full_name: "Сидоров Сидор",
    email: "sidorov@company.ru",
    role: "employee",
    department_id: 3,
  });

  await user.keyboard("{Escape}");
  expect(screen.getByDisplayValue("Tmp-12345")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Готово" }));
  await waitFor(() => expect(screen.queryByDisplayValue("Tmp-12345")).not.toBeInTheDocument());
});

test("email_taken показывается под полем email", async () => {
  mockSignedIn();
  mockUsers([]);
  server.use(
    http.post("*/api/admin/users", () =>
      HttpResponse.json(errorBody("email_taken", "Пользователь с таким email уже существует"), {
        status: 409,
      }),
    ),
  );
  const { user } = renderApp("/admin/users");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("ФИО"), "Сидоров Сидор");
  await user.type(within(dialog).getByLabelText("Email"), "petrov@company.ru");
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  expect(
    await within(dialog).findByText("Пользователь с таким email уже существует"),
  ).toBeInTheDocument();
});

test("деактивация с блокирующими причинами показывает их список", async () => {
  mockSignedIn();
  mockUsers([makeUser()]);
  server.use(
    http.post("*/api/admin/users/:id/deactivate", () =>
      HttpResponse.json(
        errorBody(
          "deactivation_blocked",
          "Перед деактивацией нужно передать ответственность другим сотрудникам",
          [{ kind: "department_head", entity_id: 3, title: "Отдел «Бухгалтерия»" }],
        ),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/admin/users");

  await openRowMenu(user, "Петров Пётр");
  await user.click(await screen.findByRole("menuitem", { name: "Деактивировать" }));
  await user.click(
    within(await screen.findByRole("dialog")).getByRole("button", { name: "Деактивировать" }),
  );

  expect(await screen.findByText("Отдел «Бухгалтерия»")).toBeInTheDocument();
  expect(screen.getByText("Руководитель отдела")).toBeInTheDocument();
});

test("редактирование отправляет только изменённые поля", async () => {
  mockSignedIn();
  mockUsers([makeUser({ role: "employee", department_id: 3 })]);
  let patched: Schemas["UserUpdate"] | null = null;
  server.use(
    http.patch("*/api/admin/users/:id", async ({ request }) => {
      patched = (await request.json()) as Schemas["UserUpdate"];
      return HttpResponse.json(makeUser({ role: "manager", department_id: 3 }));
    }),
  );
  const { user } = renderApp("/admin/users");

  await openRowMenu(user, "Петров Пётр");
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Роль"));
  await user.click(await screen.findByRole("option", { name: "Руководитель" }));
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(patched).toEqual({ role: "manager" });
});

test("администратор меняет свою роль — данные пользователя перезапрашиваются", async () => {
  mockSignedIn(makeMe({ id: 1, full_name: "Иванов Иван", role: "admin" }));
  mockUsers([makeUser({ id: 1, full_name: "Кузнецов Пётр", role: "admin", department_id: 3 })]);
  let meCalls = 0;
  server.use(
    http.get("*/api/auth/me", () => {
      meCalls += 1;
      const role = meCalls === 1 ? "admin" : "manager";
      return HttpResponse.json(makeMe({ id: 1, full_name: "Иванов Иван", role }));
    }),
    http.patch("*/api/admin/users/:id", () =>
      HttpResponse.json(makeUser({ id: 1, full_name: "Кузнецов Пётр", role: "manager" })),
    ),
  );
  const { user } = renderApp("/admin/users");

  await openRowMenu(user, "Кузнецов Пётр");
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Роль"));
  await user.click(await screen.findByRole("option", { name: "Руководитель" }));
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  await waitFor(() => expect(meCalls).toBe(2));
});
