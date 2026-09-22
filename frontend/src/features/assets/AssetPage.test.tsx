import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, makeAssetEvent, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { mockAssetLookups } from "./testing";

function mockCard(asset = makeAsset()) {
  let loads = 0;
  server.use(
    http.get("*/api/assets/100", () => {
      loads += 1;
      return HttpResponse.json(asset);
    }),
  );
  return { loads: () => loads };
}

test("меню «Действия» строится из allowed_operations", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard(makeAsset({ allowed_operations: ["issue", "write_off"] }));
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));

  const items = screen.getAllByRole("menuitem").map((item) => item.textContent);
  expect(items).toEqual(["Выдать", "Списать"]);
});

test("сотрудник видит карточку без действий", async () => {
  mockSignedIn(makeMe({ role: "employee", id: 10 }));
  mockCard(
    makeAsset({
      status: "in_use",
      owner_id: 10,
      owner_name: "Петров Пётр",
      allowed_operations: [],
    }),
  );
  renderApp("/equipment/assets/100");

  expect(await screen.findByText("INV-001 — Lenovo ThinkPad T14")).toBeInTheDocument();
  expect(screen.getByText("Петров Пётр")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Действия" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Редактировать" })).not.toBeInTheDocument();
});

test("выдача из карточки отправляет сотрудника и причину", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard();
  let body: unknown = null;
  server.use(
    http.post("*/api/assets/100/operations", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(makeAsset({ status: "in_use" }));
    }),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name: "Выдать" }));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).queryByLabelText(/Локация/)).not.toBeInTheDocument();
  await user.click(within(dialog).getByLabelText("Сотрудник"));
  await user.click(await screen.findByRole("option", { name: "Петров Пётр" }));
  await user.click(within(dialog).getByLabelText("Причина"));
  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
  expect(reasons).toEqual(["Не указана", "Новый сотрудник", "Неисправность"]);
  await user.click(screen.getByRole("option", { name: "Новый сотрудник" }));
  await user.click(within(dialog).getByRole("button", { name: "Выдать" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(body).toEqual({ operation: "issue", owner_id: 10, reason_id: 7, comment: null });
});

test("списание требует причину на клиенте", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard();
  let called = false;
  server.use(
    http.post("*/api/assets/100/operations", () => {
      called = true;
      return HttpResponse.json(makeAsset());
    }),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name: "Списать" }));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText(/Списание необратимо/)).toBeInTheDocument();
  await user.click(within(dialog).getByRole("button", { name: "Списать" }));

  expect(await within(dialog).findByText("Обязательное поле")).toBeInTheDocument();
  expect(called).toBe(false);
});

test("409 operation_not_allowed закрывает диалог и перезагружает карточку", async () => {
  mockSignedIn();
  mockAssetLookups();
  const card = mockCard();
  server.use(
    http.post("*/api/assets/100/operations", () =>
      HttpResponse.json(
        errorBody("operation_not_allowed", "Операция недоступна", { status: "in_use" }),
        {
          status: 409,
        },
      ),
    ),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name: "Зарезервировать" }));
  await user.click(
    within(await screen.findByRole("dialog")).getByRole("button", { name: "Зарезервировать" }),
  );

  expect(
    await screen.findByText("Статус техники изменился — данные обновлены"),
  ).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await waitFor(() => expect(card.loads()).toBe(2));
});

test("история показывает переходы и изменённые поля", async () => {
  mockSignedIn();
  mockCard();
  server.use(
    http.get("*/api/assets/100/events", () =>
      HttpResponse.json(
        page([
          makeAssetEvent({
            id: 3,
            event_type: "edited",
            to_status: null,
            to_location_id: null,
            to_location_name: null,
            changes: { model: ["T14", "T14 Gen 5"] },
          }),
          makeAssetEvent({
            id: 2,
            event_type: "issued",
            operation: "issue",
            from_status: "in_stock",
            to_status: "in_use",
            to_owner_id: 10,
            to_owner_name: "Петров Пётр",
            to_location_id: null,
            to_location_name: null,
            reason_name: "Новый сотрудник",
            comment: "Под подпись",
          }),
        ]),
      ),
    ),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("tab", { name: "История" }));

  expect(await screen.findByText("Модель: T14 → T14 Gen 5")).toBeInTheDocument();
  expect(screen.getByText("Статус: На складе → В работе")).toBeInTheDocument();
  expect(screen.getByText("Владелец: — → Петров Пётр")).toBeInTheDocument();
  expect(screen.getByText("Причина: Новый сотрудник")).toBeInTheDocument();
  expect(screen.getByText("Под подпись")).toBeInTheDocument();
});

test("правка при конфликте версий закрывает форму и предупреждает", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard();
  let sent: unknown = null;
  server.use(
    http.patch("*/api/assets/100", async ({ request }) => {
      sent = await request.json();
      return HttpResponse.json(
        errorBody("version_conflict", "Данные изменил другой пользователь"),
        {
          status: 409,
        },
      );
    }),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  const model = within(dialog).getByLabelText("Модель");
  await user.clear(model);
  await user.type(model, "T14 Gen 5");
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  expect(await screen.findByText(/внесите правки заново/)).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(sent).toEqual({ model: "T14 Gen 5", version: 1 });
});

test("чужая или несуществующая техника — страница «не найдена»", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  server.use(
    http.get("*/api/assets/100", () =>
      HttpResponse.json(errorBody("asset_not_found", "Техника не найдена"), { status: 404 }),
    ),
  );
  renderApp("/equipment/assets/100");

  expect(await screen.findByRole("heading", { name: "Техника не найдена" })).toBeInTheDocument();
});
