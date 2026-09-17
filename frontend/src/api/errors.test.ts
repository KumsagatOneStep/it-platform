import { http, HttpResponse } from "msw";

import { server } from "../test/server";
import { api, unwrap } from "./client";
import { ApiError, blockersOf, isRetryableError, validationIssuesOf } from "./errors";

test("ошибка в формате backend превращается в ApiError с request id", async () => {
  server.use(
    http.get("*/api/departments", () =>
      HttpResponse.json(
        { error: { code: "department_not_found", message: "Отдел не найден", details: null } },
        { status: 404, headers: { "X-Request-ID": "req-1" } },
      ),
    ),
  );

  const error = (await unwrap(api.GET("/api/departments")).catch((e: unknown) => e)) as ApiError;

  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({
    status: 404,
    code: "department_not_found",
    message: "Отдел не найден",
    requestId: "req-1",
  });
});

test("ответ не в формате backend даёт unknown_error", async () => {
  server.use(http.get("*/api/departments", () => new HttpResponse("Bad gateway", { status: 502 })));

  const error = (await unwrap(api.GET("/api/departments")).catch((e: unknown) => e)) as ApiError;

  expect(error).toMatchObject({
    status: 502,
    code: "unknown_error",
    message: "Не удалось выполнить запрос",
  });
  expect(isRetryableError(error)).toBe(true);
});

test("сетевой сбой даёт network_error", async () => {
  server.use(http.get("*/api/departments", () => HttpResponse.error()));

  const error = (await unwrap(api.GET("/api/departments")).catch((e: unknown) => e)) as ApiError;

  expect(error).toMatchObject({
    status: 0,
    code: "network_error",
    message: "Нет связи с сервером",
  });
  expect(isRetryableError(error)).toBe(true);
});

test("blockersOf и validationIssuesOf отбрасывают элементы неверной формы", () => {
  const blocked = new ApiError({
    status: 409,
    code: "deactivation_blocked",
    message: "Перед деактивацией нужно передать ответственность другим сотрудникам",
    details: [{ kind: "department_head", entity_id: 3, title: "Отдел «ИТ»" }, { kind: 1 }],
  });
  const invalid = new ApiError({
    status: 422,
    code: "validation_failed",
    message: "Некорректные данные запроса",
    details: [
      { loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" },
      "x",
    ],
  });

  expect(blockersOf(blocked)).toEqual([
    { kind: "department_head", entity_id: 3, title: "Отдел «ИТ»" },
  ]);
  expect(validationIssuesOf(invalid)).toHaveLength(1);
  expect(isRetryableError(invalid)).toBe(false);
});
