import type { Schemas } from "../../api/types";

export type Asset = Schemas["AssetRead"];
export type AssetEvent = Schemas["AssetEventRead"];
export type AssetStatus = Schemas["AssetStatus"];
export type Operation = Schemas["Operation"];

export const STATUS_LABELS: Record<AssetStatus, string> = {
  in_stock: "На складе",
  reserved: "Резерв",
  in_use: "В работе",
  in_repair: "В ремонте",
  written_off: "Списана",
};

export const STATUS_COLORS: Record<
  AssetStatus,
  "success" | "info" | "primary" | "warning" | "default"
> = {
  in_stock: "success",
  reserved: "info",
  in_use: "primary",
  in_repair: "warning",
  written_off: "default",
};

export const ASSET_STATUSES = Object.keys(STATUS_LABELS) as AssetStatus[];

export const OPERATION_LABELS: Record<Operation, string> = {
  issue: "Выдать",
  return: "Принять на склад",
  reserve: "Зарезервировать",
  unreserve: "Снять резерв",
  to_repair: "Передать в ремонт",
  repair_to_owner: "Вернуть из ремонта владельцу",
  repair_to_stock: "Вернуть из ремонта на склад",
  write_off: "Списать",
  move: "Переместить",
};

const EVENT_LABELS: Record<Schemas["AssetEventType"], string> = {
  created: "Поставлена на учёт",
  issued: "Выдача",
  returned: "Возврат на склад",
  status_changed: "Смена статуса",
  moved: "Перемещение",
  edited: "Редактирование",
  written_off: "Списание",
};

/** Название события техники: операция, если есть, иначе тип события. */
export function assetEventLabel(
  eventType: Schemas["AssetEventType"],
  operation: Operation | null,
): string {
  return operation ? OPERATION_LABELS[operation] : EVENT_LABELS[eventType];
}

/** Заголовок события: название операции, если есть, иначе тип события. */
export function eventTitle(event: AssetEvent): string {
  return assetEventLabel(event.event_type, event.operation);
}

export const FIELD_LABELS: Record<string, string> = {
  asset_type_id: "Тип",
  inventory_number: "Инв. номер",
  serial_number: "Серийный номер",
  model: "Модель",
  accepted_at: "Дата принятия к учёту",
  purchased_at: "Дата покупки",
  warranty_until: "Гарантия до",
  initial_cost: "Стоимость",
  needs_review: "Требует проверки",
};

function formatValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean") return value ? "да" : "нет";
  return String(value);
}

/** Строки «было → стало» для события: владелец, статус, локация и изменённые поля. */
export function eventChanges(event: AssetEvent): string[] {
  const lines: string[] = [];
  const pair = (label: string, from: string | null, to: string | null) => {
    if (from !== null || to !== null) lines.push(`${label}: ${from ?? "—"} → ${to ?? "—"}`);
  };
  pair(
    "Статус",
    event.from_status ? STATUS_LABELS[event.from_status] : null,
    event.to_status ? STATUS_LABELS[event.to_status] : null,
  );
  pair("Владелец", event.from_owner_name, event.to_owner_name);
  pair("Локация", event.from_location_name, event.to_location_name);
  for (const [field, value] of Object.entries(event.changes ?? {})) {
    const [from, to] = value as [unknown, unknown];
    pair(FIELD_LABELS[field] ?? field, formatValue(from), formatValue(to));
  }
  return lines;
}
