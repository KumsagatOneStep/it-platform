import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../../api/types";
import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeUser, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";

const LOCATIONS: Schemas["LocationRead"][] = [
  { id: 1, name: "Главный офис, каб. 101", description: "3 этаж", is_active: true },
];

function mockBase() {
  mockSignedIn();
  server.use(
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([makeUser({ id: 5, full_name: "Смирнова Анна", role: "manager" })])),
    ),
  );
}

test("/admin/directories открывает локации, вкладки переключают справочник", async () => {
  mockBase();
  server.use(
    http.get("*/api/directories/locations", () => HttpResponse.json(LOCATIONS)),
    http.get("*/api/directories/asset-types", () =>
      HttpResponse.json<Schemas["AssetTypeRead"][]>([{ id: 2, name: "Ноутбук", is_active: true }]),
    ),
  );
  const { user, router } = renderApp("/admin/directories");

  expect(await screen.findByText("Главный офис, каб. 101")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/admin/directories/locations");

  await user.click(screen.getByRole("tab", { name: "Типы техники" }));
  expect(await screen.findByText("Ноутбук")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/admin/directories/asset-types");
});

test("деактивация элемента и переключатель «Показывать неактивные»", async () => {
  mockBase();
  const requests: URL[] = [];
  let patched: Schemas["LocationUpdate"] | null = null;
  server.use(
    http.get("*/api/directories/locations", ({ request }) => {
      requests.push(new URL(request.url));
      return HttpResponse.json(LOCATIONS);
    }),
    http.patch("*/api/admin/directories/locations/:id", async ({ request }) => {
      patched = (await request.json()) as Schemas["LocationUpdate"];
      return HttpResponse.json({ ...LOCATIONS[0]!, is_active: false });
    }),
  );
  const { user } = renderApp("/admin/directories/locations");

  const row = (await screen.findByText("Главный офис, каб. 101")).closest("tr")!;
  await user.click(within(row).getByRole("button", { name: "Действия" }));
  await user.click(await screen.findByRole("menuitem", { name: "Деактивировать" }));
  await waitFor(() => expect(patched).toEqual({ is_active: false }));

  await user.click(screen.getByLabelText("Показывать неактивные"));
  await waitFor(() => expect(requests.at(-1)?.searchParams.get("include_inactive")).toBe("true"));
});

test("тип заявки: код задаётся при создании, дубль кода — ошибка под полем «Код»", async () => {
  mockBase();
  const ticketType: Schemas["TicketTypeRead"] = {
    id: 4,
    code: "repair",
    name: "На ремонт",
    requires_approval: true,
    default_assignee_id: 5,
    is_active: true,
  };
  server.use(
    http.get("*/api/directories/ticket-types", () => HttpResponse.json([ticketType])),
    http.post("*/api/admin/directories/ticket-types", () =>
      HttpResponse.json(
        errorBody("already_exists", "Элемент с таким значением уже существует", {
          constraint: "uq_ticket_types_code",
        }),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/admin/directories/ticket-types");

  const row = (await screen.findByText("На ремонт")).closest("tr")!;
  expect(await within(row).findByText("Смирнова Анна")).toBeInTheDocument();

  await user.click(within(row).getByRole("button", { name: "Действия" }));
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  let dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByLabelText("Код")).toBeDisabled();
  await user.click(within(dialog).getByRole("button", { name: "Отмена" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

  await user.click(screen.getByRole("button", { name: "Добавить" }));
  dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Код"), "repair");
  await user.type(within(dialog).getByLabelText("Название"), "Ремонт");
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  const codeField = within(dialog).getByLabelText("Код");
  expect(
    await within(dialog).findByText("Элемент с таким значением уже существует"),
  ).toBeInTheDocument();
  expect(codeField).toHaveAttribute("aria-invalid", "true");
});
