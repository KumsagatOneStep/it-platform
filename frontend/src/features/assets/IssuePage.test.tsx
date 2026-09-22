import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, page } from "../../test/fixtures";
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
    http.post("*/api/assets/issue", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(
        errorBody("assets_unavailable", "Часть техники недоступна", [
          { asset_id: 101, inventory_number: "INV-002", status: "in_use" },
        ]),
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

  expect(await within(section).findByText(/выделена красным/)).toBeInTheDocument();
  expect(body).toEqual({ owner_id: 10, asset_ids: [100, 101], reason_id: null, comment: null });
  const taken = within(section).getByText("INV-002 — Dell Latitude").closest(".MuiChip-root")!;
  expect(taken).toHaveClass("MuiChip-colorError");
});

test("выдача без сотрудника и техники подсказывает поля и не отправляет запрос", async () => {
  mockSignedIn();
  mockAssetLookups();
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(within(section).getByText("Выберите сотрудника")).toBeInTheDocument();
  expect(within(section).getByText("Выберите технику")).toBeInTheDocument();
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
