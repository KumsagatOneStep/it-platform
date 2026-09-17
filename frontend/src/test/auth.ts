import { http, HttpResponse } from "msw";

import type { Me, Schemas } from "../api/types";
import { errorBody } from "./http";
import { server } from "./server";

export function makeMe(overrides: Partial<Me> = {}): Me {
  return {
    id: 1,
    email: "admin@company.ru",
    full_name: "Иванов Иван",
    role: "admin",
    department_id: null,
    must_change_password: false,
    ...overrides,
  };
}

export function tokenResponse(accessToken = "token-1"): Schemas["AccessTokenResponse"] {
  return { access_token: accessToken, token_type: "bearer", must_change_password: false };
}

/** Сессия восстанавливается по refresh-cookie: refresh выдаёт токен, /me возвращает пользователя. */
export function mockSignedIn(me: Me = makeMe()): void {
  server.use(
    http.post("*/api/auth/refresh", () => HttpResponse.json(tokenResponse())),
    http.get("*/api/auth/me", () => HttpResponse.json(me)),
  );
}

/** Refresh-cookie нет: пользователь — гость. */
export function mockSignedOut(): void {
  server.use(
    http.post("*/api/auth/refresh", () =>
      HttpResponse.json(errorBody("invalid_refresh_token", "Сессия истекла, войдите снова"), {
        status: 401,
      }),
    ),
  );
}
