import { test, expect } from "vitest";

import { theme } from "./theme";

test("тема использует палитру и шрифт Modernize", () => {
  expect(theme.palette.primary.main).toBe("#5D87FF");
  expect(theme.typography.fontFamily).toContain("Manrope");
  expect(theme.shadows).toHaveLength(25);
});

test("тема подключает русскую локализацию компонентов MUI", () => {
  expect(theme.components?.MuiTablePagination?.defaultProps?.labelRowsPerPage).toBe(
    "Строк на странице:",
  );
});
