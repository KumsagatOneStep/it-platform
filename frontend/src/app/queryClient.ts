import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { isRetryableError, type ApiError } from "../api/errors";

/** Сбои сети и сервера пишутся в консоль с X-Request-ID — по нему ищется запись в логах backend. */
export function logServerError(error: unknown): void {
  if (!isRetryableError(error)) return;
  const { status, code, requestId } = error as ApiError;
  console.error("Ошибка запроса к API", { status, code, requestId });
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({ onError: logServerError }),
    mutationCache: new MutationCache({ onError: logServerError }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => isRetryableError(error) && failureCount < 2,
      },
      mutations: { retry: false },
    },
  });
}
