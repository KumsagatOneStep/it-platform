import { networkError } from "./errors";
import { getAccessToken, setAccessToken } from "./session";
import type { Schemas } from "./types";

const REFRESH_LOCK = "it-platform-refresh";

let inflight: Promise<string | null> | null = null;

/**
 * Обновляет access-токен по refresh-cookie. Одновременно выполняется не больше одного refresh:
 * внутри вкладки — общий промис, между вкладками — Web Locks API.
 * `staleToken` — токен, с которым запрос получил 401: если к моменту получения блокировки
 * токен уже сменился, сетевой refresh не нужен.
 * Возвращает новый токен или null, если сессия недействительна.
 */
export function refreshAccessToken(staleToken: string | null): Promise<string | null> {
  inflight ??= withRefreshLock(() => refreshUnlessUpdated(staleToken)).finally(() => {
    inflight = null;
  });
  return inflight;
}

async function refreshUnlessUpdated(staleToken: string | null): Promise<string | null> {
  const current = getAccessToken();
  if (current !== null && current !== staleToken) return current;

  let response: Response;
  try {
    response = await globalThis.fetch(`${window.location.origin}/api/auth/refresh`, {
      method: "POST",
      credentials: "same-origin",
    });
  } catch {
    throw networkError();
  }
  if (!response.ok) {
    setAccessToken(null);
    return null;
  }
  const body = (await response.json()) as Schemas["AccessTokenResponse"];
  setAccessToken(body.access_token);
  return body.access_token;
}

async function withRefreshLock(task: () => Promise<string | null>): Promise<string | null> {
  const locks = (navigator as Partial<Navigator>).locks;
  if (!locks) return task();
  return await locks.request(REFRESH_LOCK, task);
}
