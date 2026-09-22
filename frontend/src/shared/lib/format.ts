import type { Schemas, UserRole } from "../../api/types";

const dateFormat = new Intl.DateTimeFormat("ru-RU");
const dateTimeFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

export const ROLE_LABELS: Record<UserRole, string> = {
  employee: "Сотрудник",
  manager: "Руководитель",
  admin: "Администратор",
};

export const APPLICABILITY_LABELS: Record<Schemas["IssueReasonApplicability"], string> = {
  assets: "Техника",
  stock: "Расходники",
  both: "Техника и расходники",
};

export function initialsOf(fullName: string): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Дата «YYYY-MM-DD» по часам браузера (toISOString дал бы дату по UTC). */
export function localDateIso(date: Date = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
