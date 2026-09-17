import createClient, { type Middleware } from "openapi-fetch";

import { apiErrorFromBody, networkError, toApiError, ApiError } from "./errors";
import { refreshAccessToken } from "./refresh";
import { getAccessToken, sessionHandlers } from "./session";
import type { paths } from "./schema";

const NO_REFRESH_PATHS = new Set([
  "/api/auth/login",
  "/api/auth/refresh",
  "/api/auth/logout",
  "/api/auth/change-password",
]);

const replayableRequests = new Map<string, Request>();

function bearerOf(request: Request): string | null {
  const header = request.headers.get("Authorization");
  return header?.startsWith("Bearer ") ? header.slice("Bearer ".length) : null;
}

async function isPasswordChangeRequired(response: Response): Promise<boolean> {
  try {
    const body = (await response.clone().json()) as { error?: { code?: string } };
    return body.error?.code === "password_change_required";
  } catch {
    return false;
  }
}

const authMiddleware: Middleware = {
  onRequest({ request, id }) {
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    if (!NO_REFRESH_PATHS.has(new URL(request.url).pathname)) {
      replayableRequests.set(id, request.clone());
    }
    return request;
  },

  async onResponse({ response, id }) {
    const original = replayableRequests.get(id);
    replayableRequests.delete(id);

    if (response.status === 403 && (await isPasswordChangeRequired(response))) {
      sessionHandlers().onPasswordChangeRequired();
    }
    if (response.status !== 401 || !original) return response;

    const token = await refreshAccessToken(bearerOf(original));
    if (!token) {
      sessionHandlers().onSessionExpired();
      return response;
    }
    const retry = new Request(original, { headers: new Headers(original.headers) });
    retry.headers.set("Authorization", `Bearer ${token}`);
    const retried = await globalThis.fetch(retry);
    if (retried.status === 401) sessionHandlers().onSessionExpired();
    return retried;
  },

  onError({ id }) {
    replayableRequests.delete(id);
  },
};

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  credentials: "same-origin",
  // Ссылка на fetch берётся в момент запроса: так MSW в тестах перехватывает вызовы.
  fetch: (request) => globalThis.fetch(request),
});
api.use(authMiddleware);

interface ClientResult<D> {
  data?: D;
  error?: unknown;
  response: Response;
}

/** Возвращает данные успешного ответа или бросает ApiError. */
export async function unwrap<D>(request: Promise<ClientResult<D>>): Promise<D> {
  let result: ClientResult<D>;
  try {
    result = await request;
  } catch (error) {
    throw error instanceof ApiError
      ? error
      : error instanceof TypeError
        ? networkError()
        : toApiError(error);
  }
  if (result.response.ok) return result.data as D;
  throw apiErrorFromBody(
    result.response.status,
    result.error,
    result.response.headers.get("X-Request-ID"),
  );
}
