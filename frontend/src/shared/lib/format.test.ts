import { formatDate, formatDateTime, initialsOf, localDateIso, ROLE_LABELS } from "./format";

test("даты форматируются по-русски", () => {
  expect(formatDate("2026-09-17T10:00:00Z")).toBe("17.09.2026");
  expect(formatDateTime("2026-09-17T10:00:00Z")).toMatch(/^17\.09\.2026, \d{2}:\d{2}$/);
});

test("названия ролей и инициалы", () => {
  expect(ROLE_LABELS.manager).toBe("Руководитель");
  expect(initialsOf("Иванов  Пётр Сергеевич")).toBe("ИП");
});

test("локальная дата в формате ISO", () => {
  expect(localDateIso(new Date(2026, 8, 5, 23, 30))).toBe("2026-09-05");
});
