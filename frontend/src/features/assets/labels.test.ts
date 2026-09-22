import { makeAssetEvent } from "../../test/fixtures";
import { eventChanges, eventTitle } from "./labels";

test("заголовок события: операция важнее типа", () => {
  expect(eventTitle(makeAssetEvent())).toBe("Поставлена на учёт");
  expect(eventTitle(makeAssetEvent({ event_type: "status_changed", operation: "to_repair" }))).toBe(
    "Передать в ремонт",
  );
});

test("строки «было → стало» только для заполненных пар", () => {
  const lines = eventChanges(
    makeAssetEvent({
      event_type: "returned",
      from_status: "in_use",
      to_status: "in_stock",
      from_owner_name: "Петров Пётр",
      to_location_id: null,
      to_location_name: null,
      changes: { needs_review: [true, false] },
    }),
  );

  expect(lines).toEqual([
    "Статус: В работе → На складе",
    "Владелец: Петров Пётр → —",
    "Требует проверки: да → нет",
  ]);
});
