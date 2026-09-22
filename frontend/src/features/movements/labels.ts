import type { Schemas } from "../../api/types";
import { formatDate } from "../../shared/lib/format";
import { assetEventLabel, STATUS_LABELS } from "../assets";
import { movementTitle } from "../stock";

export type JournalEntry = Schemas["JournalEntryRead"];
export type JournalGroup = Schemas["JournalGroup"];
export type JournalKind = Schemas["JournalKind"];

export const GROUP_LABELS: Record<JournalGroup, string> = {
  issue: "Выдача",
  return: "Возврат",
  receipt: "Приход",
  write_off: "Списание",
  adjustment: "Корректировка",
  transfer: "Перемещение",
  status: "Смена статуса",
  record: "Создание и правка",
};

export const JOURNAL_GROUPS = Object.keys(GROUP_LABELS) as JournalGroup[];

export const KIND_LABELS: Record<JournalKind, string> = {
  asset: "Техника",
  stock: "Расходники",
};

export const JOURNAL_KINDS = Object.keys(KIND_LABELS) as JournalKind[];

export function entryTitle(entry: JournalEntry): string {
  if (entry.kind === "asset" && entry.asset_event_type) {
    return assetEventLabel(entry.asset_event_type, entry.asset_operation);
  }
  return entry.movement_type ? movementTitle(entry.movement_type) : "";
}

/** Строки подробностей: «было → стало» для техники, получатель расходника, причина, дата. */
export function entryDetails(entry: JournalEntry): string[] {
  const lines: string[] = [];
  const pair = (label: string, from: string | null, to: string | null) => {
    if (from !== null || to !== null) lines.push(`${label}: ${from ?? "—"} → ${to ?? "—"}`);
  };
  if (entry.kind === "asset") {
    pair(
      "Статус",
      entry.from_status ? STATUS_LABELS[entry.from_status] : null,
      entry.to_status ? STATUS_LABELS[entry.to_status] : null,
    );
    pair("Владелец", entry.from_owner_name, entry.to_owner_name);
  } else if (entry.to_owner_name) {
    lines.push(`Кому: ${entry.to_owner_name}`);
  }
  if (entry.document_date) lines.push(`Дата документа: ${formatDate(entry.document_date)}`);
  if (entry.reason_name) lines.push(`Причина: ${entry.reason_name}`);
  return lines;
}

/** Склад или локация: «откуда → куда», если менялись, иначе одно значение. */
export function entryLocation(entry: JournalEntry): string {
  const { from_location_name: from, to_location_name: to } = entry;
  if (from && to) return `${from} → ${to}`;
  return from ?? to ?? "—";
}

export function objectLink(entry: JournalEntry): string {
  return entry.kind === "asset"
    ? `/equipment/assets/${entry.object_id}`
    : `/equipment/stock/${entry.object_id}`;
}
