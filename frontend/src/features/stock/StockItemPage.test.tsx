import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeStockItem, makeStockMovement, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { localDateIso } from "../../shared/lib/format";
import { mockStockLookups } from "./testing";

function mockCard(item = makeStockItem()) {
  let loads = 0;
  server.use(
    http.get("*/api/stock-items/200", () => {
      loads += 1;
      return HttpResponse.json(item);
    }),
  );
  return { loads: () => loads };
}

function mockOperation(respond: () => Response | Promise<Response>) {
  const bodies: unknown[] = [];
  server.use(
    http.post("*/api/stock-items/200/operations", async ({ request }) => {
      bodies.push(await request.json());
      return respond();
    }),
  );
  return bodies;
}

async function openOperation(user: ReturnType<typeof renderApp>["user"], name: string) {
  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name }));
  return screen.findByRole("dialog");
}

test("карточка: сведения, низкий остаток и история движений", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard(makeStockItem({ quantity: 3, is_low: true }));
  server.use(
    http.get("*/api/stock-items/200/movements", () =>
      HttpResponse.json(
        page([
          makeStockMovement({
            id: 2,
            movement_type: "transfer_out",
            delta: -2,
            quantity_after: 3,
            counterpart_location_name: "Офис, каб. 101",
          }),
          makeStockMovement({ id: 1, document_date: "2026-09-01", comment: "Накладная 15" }),
        ]),
      ),
    ),
  );
  const { user } = renderApp("/equipment/stock/200");

  expect(await screen.findByRole("heading", { name: "Картридж HP 85A" })).toBeInTheDocument();
  expect(screen.getByText("Низкий остаток")).toBeInTheDocument();
  expect(screen.getByText("Картриджи")).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "История" }));
  const transfer = (await screen.findByText("Перемещение: отправлено")).closest("tr")!;
  expect(within(transfer).getByText("Куда: Офис, каб. 101")).toBeInTheDocument();
  expect(within(transfer).getByText("−2 шт")).toBeInTheDocument();
  const receipt = screen.getByText("Приход").closest("tr")!;
  expect(within(receipt).getByText("Дата документа: 01.09.2026")).toBeInTheDocument();
  expect(within(receipt).getByText("Накладная 15")).toBeInTheDocument();
});

test("приход: дата документа по умолчанию — сегодня, её подставляет сервер", async () => {
  mockSignedIn();
  mockStockLookups();
  const card = mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 17 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Приход");
  expect(within(dialog).getByLabelText("Дата документа")).toHaveValue(localDateIso());
  await user.type(within(dialog).getByLabelText("Количество, шт"), "5");
  await user.click(within(dialog).getByRole("button", { name: "Приход" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "receipt", quantity: 5, document_date: null, comment: null },
  ]);
  await waitFor(() => expect(card.loads()).toBeGreaterThan(1));
});

test("приход: изменённая дата документа отправляется", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 13 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Приход");
  await user.clear(within(dialog).getByLabelText("Дата документа"));
  await user.type(within(dialog).getByLabelText("Дата документа"), "2026-09-01");
  await user.type(within(dialog).getByLabelText("Количество, шт"), "1");
  await user.click(within(dialog).getByRole("button", { name: "Приход" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "receipt", quantity: 1, document_date: "2026-09-01", comment: null },
  ]);
});

test("списание: причина обязательна, количество не больше остатка", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 10 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Списать");
  await user.type(within(dialog).getByLabelText("Количество, шт"), "13");
  await user.click(within(dialog).getByRole("button", { name: "Списать" }));
  expect(within(dialog).getByText("Не больше остатка: 12 шт")).toBeInTheDocument();
  expect(within(dialog).getByText("Обязательное поле")).toBeInTheDocument();

  await user.clear(within(dialog).getByLabelText("Количество, шт"));
  await user.type(within(dialog).getByLabelText("Количество, шт"), "2");
  await user.click(within(dialog).getByLabelText("Причина"));
  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
  expect(reasons).toEqual(["Новый сотрудник", "Брак"]);
  await user.click(screen.getByRole("option", { name: "Брак" }));
  await user.click(within(dialog).getByRole("button", { name: "Списать" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([{ operation: "write_off", quantity: 2, reason_id: 8, comment: null }]);
});

test("операция при изменившемся остатке: уведомление и перезагрузка карточки", async () => {
  mockSignedIn();
  mockStockLookups();
  const card = mockCard();
  mockOperation(() =>
    HttpResponse.json(
      errorBody("insufficient_stock", "Недостаточно остатка", {
        stock_item_id: 200,
        requested: 12,
        available: 1,
      }),
      { status: 409 },
    ),
  );
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Переместить");
  const options = async () => {
    await user.click(within(dialog).getByLabelText("Куда"));
    return (await screen.findAllByRole("option")).map((option) => option.textContent);
  };
  expect(await options()).toEqual(["Офис, каб. 101"]);
  await user.click(screen.getByRole("option", { name: "Офис, каб. 101" }));
  await user.type(within(dialog).getByLabelText("Количество, шт"), "12");
  await user.click(within(dialog).getByRole("button", { name: "Переместить" }));

  expect(await screen.findByText("Остаток изменился — данные обновлены")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await waitFor(() => expect(card.loads()).toBeGreaterThan(1));
});

test("корректировка: вводится фактический остаток, изменение считается на форме", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 9 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Корректировка");
  expect(within(dialog).getByText("Учётный остаток: 12 шт")).toBeInTheDocument();
  await user.type(within(dialog).getByLabelText("Фактический остаток, шт"), "9");
  expect(within(dialog).getByText("Изменение: −3 шт")).toBeInTheDocument();
  await user.click(within(dialog).getByRole("button", { name: "Корректировка" }));
  expect(within(dialog).getByText("Обязательное поле")).toBeInTheDocument();
  await user.type(within(dialog).getByLabelText("Комментарий"), "Инвентаризация");
  await user.click(within(dialog).getByRole("button", { name: "Корректировка" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "adjustment", actual_quantity: 9, comment: "Инвентаризация" },
  ]);
});

test("деактивация позиции с остатком: сообщение backend в форме", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  let body: unknown = null;
  server.use(
    http.patch("*/api/stock-items/200", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(
        errorBody("stock_not_empty", "Деактивировать можно только позицию с нулевым остатком", {
          quantity: 12,
        }),
        { status: 409 },
      );
    }),
  );
  const { user } = renderApp("/equipment/stock/200");

  await user.click(await screen.findByRole("button", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Активна"));
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  expect(
    await within(dialog).findByText("Деактивировать можно только позицию с нулевым остатком"),
  ).toBeInTheDocument();
  expect(body).toEqual({ is_active: false, version: 1 });
});

test("у неактивной позиции нет меню «Действия»", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard(makeStockItem({ is_active: false, quantity: 0 }));
  renderApp("/equipment/stock/200");

  expect(await screen.findByRole("heading", { name: "Картридж HP 85A" })).toBeInTheDocument();
  expect(screen.getByText("Неактивна", { selector: ".MuiChip-label" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Действия" })).not.toBeInTheDocument();
});

test("несуществующая позиция — 404", async () => {
  mockSignedIn();
  server.use(
    http.get("*/api/stock-items/999", () =>
      HttpResponse.json(errorBody("stock_item_not_found", "Позиция не найдена"), { status: 404 }),
    ),
  );
  renderApp("/equipment/stock/999");

  expect(await screen.findByRole("heading", { name: "Позиция не найдена" })).toBeInTheDocument();
});

test("приход со страницы списка: позиция выбирается в диалоге", async () => {
  mockSignedIn();
  mockStockLookups();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 20 })));
  server.use(
    http.get("*/api/stock-items", () =>
      HttpResponse.json(page([makeStockItem(), makeStockItem({ id: 201, name: "Бумага A4" })])),
    ),
  );
  const { user } = renderApp("/equipment/stock");

  await user.click(await screen.findByRole("button", { name: "Приход" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Позиция"));
  await user.click(
    await screen.findByRole("option", { name: "Картридж HP 85A · Склад · остаток 12 шт" }),
  );
  await user.type(within(dialog).getByLabelText("Количество, шт"), "8");
  await user.click(within(dialog).getByRole("button", { name: "Приход" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "receipt", quantity: 8, document_date: null, comment: null },
  ]);
});
