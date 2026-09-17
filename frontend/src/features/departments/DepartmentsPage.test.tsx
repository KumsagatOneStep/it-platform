import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../../api/types";
import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeUser, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";

const HEAD = makeUser({ id: 5, full_name: "Смирнова Анна", role: "manager" });

function mockDirectory(departments: Schemas["DepartmentRead"][]) {
  server.use(
    http.get("*/api/departments", () => HttpResponse.json(departments)),
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([HEAD, makeUser({ id: 6, full_name: "Козлов Олег" })])),
    ),
  );
}

test("таблица отделов показывает имя руководителя и фильтрует по названию", async () => {
  mockSignedIn();
  mockDirectory([
    { id: 1, name: "Бухгалтерия", head_id: 5 },
    { id: 2, name: "Склад", head_id: null },
  ]);
  const { user } = renderApp("/admin/departments");

  const row = (await screen.findByText("Бухгалтерия")).closest("tr")!;
  expect(await within(row).findByText("Смирнова Анна")).toBeInTheDocument();
  expect(screen.getByText("Не назначен")).toBeInTheDocument();

  await user.type(screen.getByLabelText("Поиск по названию"), "скл");
  await waitFor(() => expect(screen.queryByText("Бухгалтерия")).not.toBeInTheDocument());
  expect(screen.getByText("Склад")).toBeInTheDocument();
});

test("создание отдела с руководителем; дубль названия — ошибка под полем", async () => {
  mockSignedIn();
  mockDirectory([]);
  const bodies: Schemas["DepartmentCreate"][] = [];
  server.use(
    http.post("*/api/admin/departments", async ({ request }) => {
      const body = (await request.json()) as Schemas["DepartmentCreate"];
      bodies.push(body);
      if (bodies.length === 1) {
        return HttpResponse.json(
          errorBody("department_name_taken", "Отдел с таким названием уже существует"),
          { status: 409 },
        );
      }
      return HttpResponse.json({ id: 9, ...body }, { status: 201 });
    }),
  );
  const { user } = renderApp("/admin/departments");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Название"), "Бухгалтерия");
  await user.click(within(dialog).getByLabelText("Руководитель"));
  // Сотрудники не предлагаются: руководителем может быть только Manager или Admin.
  expect(await screen.findByRole("option", { name: "Смирнова Анна" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "Козлов Олег" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("option", { name: "Смирнова Анна" }));
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  expect(
    await within(dialog).findByText("Отдел с таким названием уже существует"),
  ).toBeInTheDocument();

  await user.click(within(dialog).getByRole("button", { name: "Создать" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies.at(-1)).toEqual({ name: "Бухгалтерия", head_id: 5 });
});
