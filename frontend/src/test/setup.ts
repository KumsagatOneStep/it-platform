import "@testing-library/jest-dom/vitest";

import { resetSession } from "../api/session";
import { server } from "./server";

// jsdom не реализует matchMedia: эмулируем окно шириной 1280px (десктоп, брейкпоинт lg),
// чтобы useMediaQuery в тестах вёл себя как в браузере.
const TEST_VIEWPORT_WIDTH = 1280;

function matchesQuery(query: string): boolean {
  const min = /min-width:\s*([\d.]+)px/.exec(query);
  const max = /max-width:\s*([\d.]+)px/.exec(query);
  return (
    (!min || TEST_VIEWPORT_WIDTH >= Number(min[1])) &&
    (!max || TEST_VIEWPORT_WIDTH <= Number(max[1]))
  );
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string): MediaQueryList =>
    ({
      matches: matchesQuery(query),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList,
});

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetSession();
});
afterAll(() => server.close());
