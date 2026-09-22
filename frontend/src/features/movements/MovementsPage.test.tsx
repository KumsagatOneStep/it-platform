import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeJournalEntry, makeUser, page } from "../../test/fixtures";
import { server } from "../../test/server";

const usersRequests: URL[] = [];

function mockJournal(seen: URL[] = []) {
  server.use(
    http.get("*/api/directories/locations", () =>
      HttpResponse.json([{ id: 5, name: "Склад", description: null, is_active: true }]),
    ),
    http.get("*/api/admin/users", ({ request }) => {
      usersRequests.push(new URL(request.url));
      return HttpResponse.json(page([makeUser({ id: 10, full_name: "Петров Пётр" })]));
    }),
    http.get("*/api/equipment/movements", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(
        page([
          makeJournalEntry({ id: 7, reason_name: "Новый сотрудник" }),
          makeJournalEntry({
            kind: "asset",
            id: 3,
            asset_event_type: "issued",
            asset_operation: "issue",
            movement_type: null,
            object_id: 100,
            object_label: "INV-001 — Lenovo ThinkPad T14",
            delta: null,
            quantity_after: null,
            unit: null,
            from_status: "in_stock",
            to_status: "in_use",
            to_location_id: null,
            to_location_name: null,
          }),
        ]),
      );
    }),
  );
  return seen;
}

test("журнал: техника и расходники, ссылки на карточки, фильтры из URL", async () => {
  mockSignedIn();
  const seen = mockJournal();
  const { user, router } = renderApp(
    "/equipment/movements?from=2026-09-01&to=2026-09-22&kind=stock&group=issue&person=10&location=5",
  );

  const stockRow = (await screen.findByRole("link", { name: "Картридж HP 85A" })).closest("tr")!;
  expect(within(stockRow).getByText("Выдача")).toBeInTheDocument();
  expect(within(stockRow).getByText("−2 шт")).toBeInTheDocument();
  expect(within(stockRow).getByText("Кому: Петров Пётр")).toBeInTheDocument();
  expect(within(stockRow).getByText("Причина: Новый сотрудник")).toBeInTheDocument();
  const assetLink = screen.getByRole("link", { name: "INV-001 — Lenovo ThinkPad T14" });
  expect(assetLink).toHaveAttribute("href", "/equipment/assets/100");
  expect(
    within(assetLink.closest("tr")!).getByText("Статус: На складе → В работе"),
  ).toBeInTheDocument();

  const params = seen.at(-1)!.searchParams;
  expect(params.get("date_from")).toBe("2026-09-01");
  expect(params.get("date_to")).toBe("2026-09-22");
  expect(params.get("kind")).toBe("stock");
  expect(params.getAll("group")).toEqual(["issue"]);
  expect(params.get("person_id")).toBe("10");
  expect(params.get("location_id")).toBe("5");

  await user.click(screen.getByLabelText("Операция"));
  await user.click(await screen.findByRole("option", { name: "Списание" }));
  await waitFor(() => expect(seen.at(-1)!.searchParams.getAll("group")).toEqual(["write_off"]));
  expect(router.state.location.search).toContain("group=write_off");

  await user.click(screen.getByLabelText("Кто выполнил"));
  await screen.findByRole("option", { name: "Петров Пётр" });
  // Фильтр по людям находит и деактивированных: история уволенного сотрудника сохраняется.
  expect(usersRequests.some((url) => url.searchParams.has("is_active"))).toBe(false);
  await user.keyboard("{Escape}");

  await user.click(assetLink);
  expect(router.state.location.pathname).toBe("/equipment/assets/100");
});

test("журнал доступен только администратору", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  renderApp("/equipment/movements");

  expect(await screen.findByRole("heading", { name: "Нет доступа" })).toBeInTheDocument();
});
