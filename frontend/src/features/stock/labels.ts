import type { Schemas } from "../../api/types";
import { formatDate } from "../../shared/lib/format";

export type StockItem = Schemas["StockItemRead"];
export type StockMovement = Schemas["StockMovementRead"];
export type StockMovementType = Schemas["StockMovementType"];
export type StockOperation = "receipt" | "write_off" | "adjustment" | "transfer";

export const MOVEMENT_LABELS: Record<StockMovementType, string> = {
  receipt: "Приход",
  issue: "Выдача",
  write_off: "Списание",
  adjustment: "Корректировка",
  transfer_out: "Перемещение: отправлено",
  transfer_in: "Перемещение: получено",
};

export const STOCK_OPERATION_LABELS: Record<StockOperation, string> = {
  receipt: "Приход",
  write_off: "Списать",
  adjustment: "Корректировка",
  transfer: "Переместить",
};

export const STOCK_OPERATIONS = Object.keys(STOCK_OPERATION_LABELS) as StockOperation[];

export function movementTitle(type: StockMovementType): string {
  return MOVEMENT_LABELS[type];
}

/** «+10 шт» / «−3 шт» (минус — типографский). */
export function formatDelta(delta: number, unit: string): string {
  return `${delta > 0 ? "+" : "−"}${Math.abs(delta)} ${unit}`;
}

/** Строки подробностей движения для истории позиции. */
export function movementDetails(movement: StockMovement): string[] {
  const lines: string[] = [];
  if (movement.recipient_name) lines.push(`Кому: ${movement.recipient_name}`);
  if (movement.counterpart_location_name) {
    const label = movement.movement_type === "transfer_out" ? "Куда" : "Откуда";
    lines.push(`${label}: ${movement.counterpart_location_name}`);
  }
  if (movement.document_date) lines.push(`Дата документа: ${formatDate(movement.document_date)}`);
  if (movement.reason_name) lines.push(`Причина: ${movement.reason_name}`);
  return lines;
}
