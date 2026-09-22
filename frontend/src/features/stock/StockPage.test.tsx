import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeStockItem, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { mockStockLookups } from "./testing";

function mockItems(seen: URL[] = []) {
  server.use(
    http.get("*/api/stock-items", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(
        page([
          makeStockItem({ id: 200, quantity: 3, is_low: true }),
          makeStockItem({
            id: 201,
            name: "Бумага A4",
            category_name: "Бумага",
            unit: "пачка",
            quantity: 40,
            min_quantity: 0,
          }),
        ]),
      );
    }),
  );
  return seen;
}

test("расходники: остатки, низкий остаток красным, фильтры из URL", async () => {
  mockSignedIn();
  mockStockLookups();
  const seen = mockItems();
  const { user, router } = renderApp("/equipment/stock?category=3&low=true");

  const low = (await screen.findByRole("link", { name: "Картридж HP 85A" })).closest("tr")!;
  expect(within(low).getByText("3 шт").closest(".MuiChip-root")).toHaveClass("MuiChip-colorError");
  expect(within(low).getByText("5 шт")).toBeInTheDocument();
  const paper = screen.getByRole("link", { name: "Бумага A4" }).closest("tr")!;
  expect(within(paper).getByText("40 пачка").closest(".MuiChip-root")).not.toHaveClass(
    "MuiChip-colorError",
  );
  expect(within(paper).getByText("—")).toBeInTheDocument();
  expect(seen.at(-1)?.searchParams.get("category_id")).toBe("3");
  expect(seen.at(-1)?.searchParams.get("low_stock")).toBe("true");

  await user.click(screen.getByLabelText("Показать неактивные"));
  await waitFor(() => expect(seen.at(-1)?.searchParams.get("include_inactive")).toBe("true"));
  expect(router.state.location.search).toContain("inactive=true");
});

test("администратор добавляет позицию и попадает в её карточку", async () => {
  mockSignedIn();
  mockStockLookups();
  mockItems();
  let created: unknown = null;
  server.use(
    http.post("*/api/stock-items", async ({ request }) => {
      created = await request.json();
      return HttpResponse.json(makeStockItem({ id: 202, quantity: 0 }), { status: 201 });
    }),
  );
  const { user, router } = renderApp("/equipment/stock");

  await user.click(await screen.findByRole("button", { name: "Добавить позицию" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Наименование"), "Тонер Kyocera");
  await user.click(within(dialog).getByLabelText("Категория"));
  await user.click(await screen.findByRole("option", { name: "Картриджи" }));
  await user.clear(within(dialog).getByLabelText("Единица измерения"));
  await user.type(within(dialog).getByLabelText("Единица измерения"), "шт");
  await user.click(within(dialog).getByLabelText("Склад"));
  await user.click(await screen.findByRole("option", { name: "Офис, каб. 101" }));
  await user.type(within(dialog).getByLabelText("Минимальный остаток"), "2");
  await user.click(within(dialog).getByRole("button", { name: "Добавить" }));

  await waitFor(() => expect(router.state.location.pathname).toBe("/equipment/stock/202"));
  expect(created).toEqual({
    name: "Тонер Kyocera",
    stock_category_id: 3,
    unit: "шт",
    location_id: 6,
    min_quantity: 2,
  });
});

test("добавление: наименование занято — ошибка у поля", async () => {
  mockSignedIn();
  mockStockLookups();
  mockItems();
  server.use(
    http.post("*/api/stock-items", () =>
      HttpResponse.json(
        errorBody("stock_item_name_taken", "На этом складе уже есть позиция с таким наименованием"),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/equipment/stock");

  await user.click(await screen.findByRole("button", { name: "Добавить позицию" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Наименование"), "Картридж HP 85A");
  await user.click(within(dialog).getByLabelText("Категория"));
  await user.click(await screen.findByRole("option", { name: "Картриджи" }));
  await user.click(within(dialog).getByLabelText("Склад"));
  await user.click(await screen.findByRole("option", { name: "Склад" }));
  await user.click(within(dialog).getByRole("button", { name: "Добавить" }));

  expect(
    await within(dialog).findByText("На этом складе уже есть позиция с таким наименованием"),
  ).toBeInTheDocument();
});

test("расходники доступны только администратору", async () => {
  mockSignedIn(makeMe({ role: "manager" }));
  renderApp("/equipment/stock");

  expect(await screen.findByRole("heading", { name: "Нет доступа" })).toBeInTheDocument();
});
