import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, makeStockItem, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { mockAssetLookups } from "./testing";

const FREE = [
  makeAsset({ id: 100, inventory_number: "INV-001" }),
  makeAsset({ id: 101, inventory_number: "INV-002", model: "Dell Latitude" }),
];

async function pickEmployee(
  user: ReturnType<typeof renderApp>["user"],
  section: HTMLElement,
  label: string,
) {
  await user.click(within(section).getByLabelText(label));
  await user.click(await screen.findByRole("option", { name: "Петров Пётр" }));
}

test("выдача: при 409 недоступная техника подсвечивается, форма остаётся", async () => {
  mockSignedIn();
  mockAssetLookups();
  let body: unknown = null;
  server.use(
    http.get("*/api/assets", ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.getAll("status")).toEqual(["in_stock"]);
      return HttpResponse.json(page(FREE));
    }),
    http.post("*/api/equipment/checkout", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(
        errorBody("checkout_unavailable", "Часть техники недоступна", {
          assets: [{ asset_id: 101, inventory_number: "INV-002", status: "in_use" }],
          stock: [],
        }),
        { status: 409 },
      );
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await pickEmployee(user, section, "Кому");
  await user.click(within(section).getByLabelText("Техника"));
  await user.click(await screen.findByRole("option", { name: "INV-001 — Lenovo ThinkPad T14" }));
  await user.click(within(section).getByLabelText("Техника"));
  await user.click(await screen.findByRole("option", { name: "INV-002 — Dell Latitude" }));
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(await within(section).findByText(/выделены красным/)).toBeInTheDocument();
  expect(body).toEqual({
    recipient_id: 10,
    asset_ids: [100, 101],
    stock_lines: [],
    reason_id: null,
    comment: null,
  });
  const taken = within(section).getByText("INV-002 — Dell Latitude").closest(".MuiChip-root")!;
  expect(taken).toHaveClass("MuiChip-colorError");
});

test("выдача: 422 recipient_invalid показывает ошибку у поля «Кому», а не только в баннере", async () => {
  mockSignedIn();
  mockAssetLookups();
  server.use(
    http.get("*/api/assets", () => HttpResponse.json(page(FREE))),
    http.post("*/api/equipment/checkout", () =>
      HttpResponse.json(errorBody("recipient_invalid", "Сотрудник недоступен для выдачи"), {
        status: 422,
      }),
    ),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await pickEmployee(user, section, "Кому");
  await user.click(within(section).getByLabelText("Техника"));
  await user.click(await screen.findByRole("option", { name: "INV-001 — Lenovo ThinkPad T14" }));
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(await within(section).findByText("Сотрудник недоступен для выдачи")).toBeInTheDocument();
  expect(within(section).queryByRole("alert")).not.toBeInTheDocument();
});

function mockStockOptions() {
  server.use(
    http.get("*/api/stock-items", () =>
      HttpResponse.json(
        page([
          makeStockItem(),
          makeStockItem({ id: 201, name: "Бумага A4", unit: "пачка", quantity: 0 }),
        ]),
      ),
    ),
  );
}

async function addStockLine(
  user: ReturnType<typeof renderApp>["user"],
  section: HTMLElement,
  quantity: string,
) {
  await user.click(within(section).getByRole("button", { name: "Добавить расходник" }));
  const pickers = within(section).getAllByLabelText("Расходник");
  await user.click(pickers.at(-1)!);
  await user.click(
    await screen.findByRole("option", { name: "Картридж HP 85A · Склад · остаток 12 шт" }),
  );
  const quantities = within(section).getAllByLabelText("Количество");
  await user.type(quantities.at(-1)!, quantity);
}

test("выдача техники и расходников одной отправкой; причины — только общие", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockStockOptions();
  let body: unknown = null;
  server.use(
    http.get("*/api/assets", () => HttpResponse.json(page(FREE))),
    http.post("*/api/equipment/checkout", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json({
        assets: [makeAsset({ id: 100, status: "in_use" })],
        stock_items: [makeStockItem({ quantity: 10 })],
      });
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await pickEmployee(user, section, "Кому");
  await user.click(within(section).getByLabelText("Техника"));
  await user.click(await screen.findByRole("option", { name: "INV-001 — Lenovo ThinkPad T14" }));
  await addStockLine(user, section, "2");
  await user.click(within(section).getByLabelText("Причина"));
  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
  expect(reasons).toEqual(["Не указана", "Новый сотрудник"]);
  await user.click(screen.getByRole("option", { name: "Новый сотрудник" }));
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(await screen.findByText("Выдано позиций: 2")).toBeInTheDocument();
  expect(body).toEqual({
    recipient_id: 10,
    asset_ids: [100],
    stock_lines: [{ stock_item_id: 200, quantity: 2 }],
    reason_id: 7,
    comment: null,
  });
});

test("расходники: количество больше остатка не отправляется, позиции без остатка не предлагаются", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockStockOptions();
  let posted = false;
  server.use(
    http.post("*/api/equipment/checkout", () => {
      posted = true;
      return HttpResponse.json({ assets: [], stock_items: [] });
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await pickEmployee(user, section, "Кому");
  await user.click(within(section).getByRole("button", { name: "Добавить расходник" }));
  await user.click(within(section).getByLabelText("Расходник"));
  expect(await screen.findByRole("option", { name: /Картридж HP 85A/ })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /Бумага A4/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole("option", { name: /Картридж HP 85A/ }));
  await user.type(within(section).getByLabelText("Количество"), "13");
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(await within(section).findByText("Доступно 12 шт")).toBeInTheDocument();
  expect(posted).toBe(false);
});

test("расходники: при 409 у строки показывается остаток на сервере", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockStockOptions();
  server.use(
    http.post("*/api/equipment/checkout", () =>
      HttpResponse.json(
        errorBody("checkout_unavailable", "Часть недоступна", {
          assets: [],
          stock: [{ stock_item_id: 200, name: "Картридж HP 85A", requested: 5, available: 1 }],
        }),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await pickEmployee(user, section, "Кому");
  await addStockLine(user, section, "5");
  await user.click(within(section).getByLabelText("Причина"));
  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
  expect(reasons).toEqual(["Не указана", "Новый сотрудник", "Заправка"]);
  await user.keyboard("{Escape}");
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(await within(section).findByText(/выделены красным/)).toBeInTheDocument();
  expect(within(section).getByText("На складе осталось 1 шт")).toBeInTheDocument();
});

test("выдача без сотрудника и техники подсказывает поля и не отправляет запрос", async () => {
  mockSignedIn();
  mockAssetLookups();
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(within(section).getByText("Выберите сотрудника")).toBeInTheDocument();
  expect(within(section).getByText("Выберите технику или расходники")).toBeInTheDocument();
});

test("приём: техника сотрудника в работе, отмеченное уходит на склад", async () => {
  mockSignedIn();
  mockAssetLookups();
  let body: unknown = null;
  server.use(
    http.get("*/api/assets", ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.get("owner_id")).toBe("10");
      expect(url.searchParams.getAll("status")).toEqual(["in_use"]);
      return HttpResponse.json(
        page(FREE.map((asset) => ({ ...asset, status: "in_use" as const, owner_id: 10 }))),
      );
    }),
    http.post("*/api/assets/return", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json([makeAsset({ id: 101 })]);
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Принять" });
  expect(within(section).getByRole("button", { name: "Принять на склад" })).toBeDisabled();
  await pickEmployee(user, section, "От кого");
  await user.click(await within(section).findByLabelText("INV-002 — Dell Latitude"));
  await user.click(within(section).getByLabelText("Локация (если меняется)"));
  await user.click(await screen.findByRole("option", { name: "Офис, каб. 101" }));
  await user.click(within(section).getByRole("button", { name: "Принять на склад" }));

  expect(await screen.findByText("Принято на склад: 1")).toBeInTheDocument();
  expect(body).toEqual({ asset_ids: [101], location_id: 6, comment: null });
});

test("приём: ошибка не assets_unavailable не сбрасывает отмеченную технику", async () => {
  mockSignedIn();
  mockAssetLookups();
  server.use(
    http.get("*/api/assets", ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.get("owner_id")).toBe("10");
      expect(url.searchParams.getAll("status")).toEqual(["in_use"]);
      return HttpResponse.json(
        page(FREE.map((asset) => ({ ...asset, status: "in_use" as const, owner_id: 10 }))),
      );
    }),
    http.post("*/api/assets/return", () =>
      HttpResponse.json(errorBody("operation_not_allowed", "Операция недоступна"), {
        status: 409,
      }),
    ),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Принять" });
  await pickEmployee(user, section, "От кого");
  const checkbox = await within(section).findByLabelText("INV-002 — Dell Latitude");
  await user.click(checkbox);
  await user.click(within(section).getByRole("button", { name: "Принять на склад" }));

  expect(await within(section).findByText("Операция недоступна")).toBeInTheDocument();
  expect(checkbox).toBeChecked();
});

test("приём: после очистки «От кого» техника прежнего сотрудника пропадает со страницы", async () => {
  mockSignedIn();
  mockAssetLookups();
  server.use(
    http.get("*/api/assets", ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.get("owner_id")).toBe("10");
      return HttpResponse.json(
        page(FREE.map((asset) => ({ ...asset, status: "in_use" as const, owner_id: 10 }))),
      );
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Принять" });
  await pickEmployee(user, section, "От кого");
  expect(await within(section).findByLabelText("INV-002 — Dell Latitude")).toBeInTheDocument();

  await user.click(within(section).getByRole("button", { name: "Очистить" }));

  expect(within(section).queryByLabelText("INV-002 — Dell Latitude")).not.toBeInTheDocument();
  expect(within(section).queryByText("У сотрудника нет техники в работе")).not.toBeInTheDocument();
});

test("приём: нельзя отметить больше 50 единиц техники за раз", async () => {
  mockSignedIn();
  mockAssetLookups();
  const many = Array.from({ length: 51 }, (_, index) =>
    makeAsset({
      id: 200 + index,
      inventory_number: `INV-${200 + index}`,
      status: "in_use",
      owner_id: 10,
    }),
  );
  server.use(http.get("*/api/assets", () => HttpResponse.json(page(many, many.length))));
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Принять" });
  await pickEmployee(user, section, "От кого");
  await within(section).findByLabelText("INV-200 — Lenovo ThinkPad T14");

  for (const asset of many) {
    await user.click(
      within(section).getByLabelText(`${asset.inventory_number} — Lenovo ThinkPad T14`),
    );
  }

  expect(within(section).getByText("Не больше 50 единиц за раз")).toBeInTheDocument();
  const checkboxes = within(section).getAllByRole("checkbox") as HTMLInputElement[];
  expect(checkboxes.filter((box) => box.checked)).toHaveLength(50);
}, 15_000); // 51 клик: при параллельном прогоне всех файлов не укладывается в 5 с по умолчанию

test("страница выдачи доступна только администратору", async () => {
  mockSignedIn(makeMe({ role: "manager" }));
  renderApp("/equipment/issue");

  await waitFor(() =>
    expect(screen.queryByRole("region", { name: "Выдать" })).not.toBeInTheDocument(),
  );
  expect(
    await screen.findByRole("heading", { name: /нет доступа|не найдена/i }),
  ).toBeInTheDocument();
});
