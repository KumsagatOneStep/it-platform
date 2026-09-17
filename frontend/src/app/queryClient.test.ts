import { test, expect, vi } from "vitest";

import { ApiError } from "../api/errors";
import { createQueryClient, logServerError } from "./queryClient";

const error = (status: number) =>
  new ApiError({ status, code: "x", message: "x", requestId: "req-7" });

test("запросы повторяются только при сетевых ошибках и 5xx, не более двух раз", () => {
  const retry = createQueryClient().getDefaultOptions().queries?.retry as (
    failureCount: number,
    error: unknown,
  ) => boolean;

  expect(retry(0, error(0))).toBe(true);
  expect(retry(1, error(503))).toBe(true);
  expect(retry(2, error(503))).toBe(false);
  expect(retry(0, error(404))).toBe(false);
  expect(retry(0, new Error("x"))).toBe(false);
});

test("сбои сети и сервера логируются с request id, ошибки 4xx — нет", () => {
  const log = vi.spyOn(console, "error").mockImplementation(() => undefined);

  logServerError(error(404));
  logServerError(error(502));

  expect(log).toHaveBeenCalledTimes(1);
  expect(log).toHaveBeenCalledWith("Ошибка запроса к API", {
    status: 502,
    code: "x",
    requestId: "req-7",
  });
  log.mockRestore();
});
