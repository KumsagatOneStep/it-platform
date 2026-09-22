import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, page } from "../../test/fixtures";
import { server } from "../../test/server";
import { mockAssetLookups } from "./testing";

function mockAssets(seen: URL[] = []) {
  server.use(
    http.get("*/api/assets", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(
        page([makeAsset({ status: "in_use", owner_id: 10, owner_name: "Петров Пётр" })]),
      );
    }),
  );
  return seen;
}

test("реестр: строки, фильтры из URL и поиск", async () => {
  mockSignedIn();
  mockAssetLookups();
  const seen = mockAssets();
  const { user, router } = renderApp("/equipment/assets?status=in_use&type=1");

  const row = (await screen.findByRole("link", { name: "INV-001" })).closest("tr")!;
  expect(within(row).getByText("В работе")).toBeInTheDocument();
  expect(within(row).getByText("Петров Пётр")).toBeInTheDocument();
  expect(seen.at(-1)?.searchParams.getAll("status")).toEqual(["in_use"]);
  expect(seen.at(-1)?.searchParams.get("asset_type_id")).toBe("1");

  await user.type(screen.getByLabelText("Инв. номер, серийный номер, модель"), "t14");
  await waitFor(() => expect(seen.at(-1)?.searchParams.get("q")).toBe("t14"));
  expect(router.state.location.search).toContain("q=t14");

  await user.click(screen.getByRole("link", { name: "INV-001" }));
  expect(router.state.location.pathname).toBe("/equipment/assets/100");
});

test("сотрудник видит свою технику без кнопки «Добавить» и фильтра владельца", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  mockAssetLookups();
  mockAssets();
  renderApp("/equipment/assets");

  expect(await screen.findByText("Ваша техника")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Добавить" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Владелец")).not.toBeInTheDocument();
});

test("руководитель видит подпись области отдела", async () => {
  mockSignedIn(makeMe({ role: "manager", department_id: 3 }));
  mockAssetLookups();
  mockAssets();
  renderApp("/equipment/assets");

  expect(await screen.findByText("Техника сотрудников вашего отдела")).toBeInTheDocument();
});

test("администратор добавляет технику и попадает в карточку", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockAssets();
  let created: Record<string, unknown> | null = null;
  server.use(
    http.post("*/api/assets", async ({ request }) => {
      created = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(makeAsset({ id: 101 }), { status: 201 });
    }),
    http.get("*/api/assets/101", () => HttpResponse.json(makeAsset({ id: 101 }))),
  );
  const { user, router } = renderApp("/equipment/assets");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Тип"));
  await user.click(await screen.findByRole("option", { name: "Ноутбук" }));
  await user.type(within(dialog).getByLabelText("Инвентарный номер"), "INV-777");
  await user.type(within(dialog).getByLabelText("Модель"), "Dell Latitude");
  await user.click(within(dialog).getByLabelText("Локация"));
  await user.click(await screen.findByRole("option", { name: "Склад" }));
  await user.type(within(dialog).getByLabelText("Стоимость, ₽"), "1200,50");
  await user.click(within(dialog).getByRole("button", { name: "Добавить" }));

  await waitFor(() => expect(router.state.location.pathname).toBe("/equipment/assets/101"));
  expect(created).toMatchObject({
    asset_type_id: 1,
    inventory_number: "INV-777",
    model: "Dell Latitude",
    location_id: 5,
    serial_number: null,
    initial_cost: "1200.50",
  });
});
