import { makeJournalEntry } from "../../test/fixtures";
import { entryDetails, entryLocation, entryTitle, objectLink } from "./labels";

const assetEntry = makeJournalEntry({
  kind: "asset",
  asset_event_type: "returned",
  asset_operation: "repair_to_stock",
  movement_type: null,
  object_id: 100,
  object_label: "INV-001 — Lenovo ThinkPad T14",
  delta: null,
  quantity_after: null,
  unit: null,
  from_owner_name: "Петров Пётр",
  to_owner_id: null,
  to_owner_name: null,
  from_status: "in_repair",
  to_status: "in_stock",
  from_location_name: "Сервис",
  to_location_name: "Склад",
});

test("заголовок: операция техники, тип события или тип движения", () => {
  expect(entryTitle(assetEntry)).toBe("Вернуть из ремонта на склад");
  expect(entryTitle({ ...assetEntry, asset_operation: null, asset_event_type: "created" })).toBe(
    "Поставлена на учёт",
  );
  expect(entryTitle(makeJournalEntry())).toBe("Выдача");
});

test("подробности: статус, владелец, получатель, причина, дата документа", () => {
  expect(entryDetails(assetEntry)).toEqual([
    "Статус: В ремонте → На складе",
    "Владелец: Петров Пётр → —",
  ]);
  expect(entryDetails(makeJournalEntry({ reason_name: "Новый сотрудник" }))).toEqual([
    "Кому: Петров Пётр",
    "Причина: Новый сотрудник",
  ]);
  expect(
    entryDetails(
      makeJournalEntry({
        movement_type: "receipt",
        to_owner_name: null,
        document_date: "2026-09-01",
      }),
    ),
  ).toEqual(["Дата документа: 01.09.2026"]);
});

test("склад или локация и ссылка на карточку", () => {
  expect(entryLocation(assetEntry)).toBe("Сервис → Склад");
  expect(entryLocation(makeJournalEntry())).toBe("Склад");
  expect(entryLocation({ ...assetEntry, from_location_name: null, to_location_name: null })).toBe(
    "—",
  );
  expect(objectLink(assetEntry)).toBe("/equipment/assets/100");
  expect(objectLink(makeJournalEntry())).toBe("/equipment/stock/200");
});
