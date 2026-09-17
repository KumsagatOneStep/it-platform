import { delay, http, HttpResponse } from "msw";

import { errorBody } from "../test/http";
import { server } from "../test/server";
import { api, unwrap } from "./client";
import { ApiError } from "./errors";
import { getAccessToken, setAccessToken, setSessionHandlers } from "./session";
import type { Schemas } from "./types";

const department: Schemas["DepartmentRead"] = { id: 1, name: "ИТ", head_id: null };

function refreshHandler(counter: { calls: number }, token = "fresh") {
  return http.post("*/api/auth/refresh", async () => {
    counter.calls += 1;
    await delay(10);
    return HttpResponse.json<Schemas["AccessTokenResponse"]>({
      access_token: token,
      token_type: "bearer",
      must_change_password: false,
    });
  });
}

function departmentsRequiring(token: string) {
  return http.get("*/api/departments", ({ request }) =>
    request.headers.get("Authorization") === `Bearer ${token}`
      ? HttpResponse.json<Schemas["DepartmentRead"][]>([department])
      : HttpResponse.json(errorBody("unauthorized", "Требуется вход"), { status: 401 }),
  );
}

function trackSession() {
  const calls = { expired: 0, passwordChange: 0 };
  setSessionHandlers({
    onSessionExpired: () => (calls.expired += 1),
    onPasswordChangeRequired: () => (calls.passwordChange += 1),
  });
  return calls;
}

test("подставляет access-токен в заголовок Authorization", async () => {
  setAccessToken("t1");
  server.use(departmentsRequiring("t1"));

  await expect(unwrap(api.GET("/api/departments"))).resolves.toEqual([department]);
});

test("параллельные 401 приводят ровно к одному refresh и повтору всех запросов", async () => {
  setAccessToken("stale");
  const refresh = { calls: 0 };
  server.use(refreshHandler(refresh), departmentsRequiring("fresh"));

  const results = await Promise.all([
    unwrap(api.GET("/api/departments")),
    unwrap(api.GET("/api/departments")),
    unwrap(api.GET("/api/departments")),
  ]);

  expect(results).toEqual([[department], [department], [department]]);
  expect(refresh.calls).toBe(1);
  expect(getAccessToken()).toBe("fresh");
});

test("повтор запроса отправляет тело исходного запроса", async () => {
  setAccessToken("stale");
  server.use(
    refreshHandler({ calls: 0 }),
    http.patch("*/api/admin/departments/:id", async ({ request }) => {
      if (request.headers.get("Authorization") !== "Bearer fresh") {
        return HttpResponse.json(errorBody("unauthorized", "Требуется вход"), { status: 401 });
      }
      const body = (await request.json()) as Schemas["DepartmentUpdate"];
      return HttpResponse.json<Schemas["DepartmentRead"]>({ ...department, name: body.name ?? "" });
    }),
  );

  const updated = await unwrap(
    api.PATCH("/api/admin/departments/{department_id}", {
      params: { path: { department_id: 1 } },
      body: { name: "Бухгалтерия" },
    }),
  );

  expect(updated.name).toBe("Бухгалтерия");
});

test("неудачный refresh завершает сессию и отдаёт ошибку 401", async () => {
  setAccessToken("stale");
  const session = trackSession();
  server.use(
    http.post("*/api/auth/refresh", () =>
      HttpResponse.json(errorBody("invalid_refresh_token", "Сессия истекла, войдите снова"), {
        status: 401,
      }),
    ),
    departmentsRequiring("fresh"),
  );

  const error = await unwrap(api.GET("/api/departments")).catch((e: unknown) => e);

  expect(error).toBeInstanceOf(ApiError);
  expect((error as ApiError).status).toBe(401);
  expect(session.expired).toBe(1);
  expect(getAccessToken()).toBeNull();
});

test("401 после успешного refresh тоже завершает сессию", async () => {
  setAccessToken("stale");
  const session = trackSession();
  server.use(refreshHandler({ calls: 0 }), departmentsRequiring("never"));

  await expect(unwrap(api.GET("/api/departments"))).rejects.toMatchObject({ status: 401 });
  expect(session.expired).toBe(1);
});

test("401 на вход не запускает refresh", async () => {
  const refresh = { calls: 0 };
  server.use(
    refreshHandler(refresh),
    http.post("*/api/auth/login", () =>
      HttpResponse.json(errorBody("invalid_credentials", "Неверный email или пароль"), {
        status: 401,
      }),
    ),
  );

  await expect(
    unwrap(api.POST("/api/auth/login", { body: { email: "a@b.ru", password: "x" } })),
  ).rejects.toMatchObject({ code: "invalid_credentials", message: "Неверный email или пароль" });
  expect(refresh.calls).toBe(0);
});

test("403 password_change_required сообщает о необходимости сменить пароль", async () => {
  setAccessToken("t1");
  const session = trackSession();
  server.use(
    http.get("*/api/departments", () =>
      HttpResponse.json(errorBody("password_change_required", "Необходимо сменить пароль"), {
        status: 403,
      }),
    ),
  );

  await expect(unwrap(api.GET("/api/departments"))).rejects.toMatchObject({
    code: "password_change_required",
  });
  expect(session.passwordChange).toBe(1);
});
