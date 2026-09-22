import { http, HttpResponse } from "msw";

import { makeUser, page } from "../../test/fixtures";
import { server } from "../../test/server";

/** Справочники и пользователи, которые запрашивают экраны техники. */
export function mockAssetLookups() {
  server.use(
    http.get("*/api/directories/locations", () =>
      HttpResponse.json([
        { id: 5, name: "Склад", description: null, is_active: true },
        { id: 6, name: "Офис, каб. 101", description: null, is_active: true },
      ]),
    ),
    http.get("*/api/directories/asset-types", () =>
      HttpResponse.json([{ id: 1, name: "Ноутбук", is_active: true }]),
    ),
    http.get("*/api/directories/issue-reasons", () =>
      HttpResponse.json([
        { id: 7, name: "Новый сотрудник", applicability: "both", is_active: true },
        { id: 8, name: "Заправка", applicability: "stock", is_active: true },
        { id: 9, name: "Неисправность", applicability: "assets", is_active: true },
      ]),
    ),
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([makeUser({ id: 10, full_name: "Петров Пётр" })])),
    ),
  );
}
