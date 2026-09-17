import type { Schemas } from "../api/types";

export function makeUser(overrides: Partial<Schemas["UserRead"]> = {}): Schemas["UserRead"] {
  return {
    id: 10,
    email: "petrov@company.ru",
    full_name: "Петров Пётр",
    role: "employee",
    department_id: null,
    is_active: true,
    must_change_password: false,
    created_at: "2026-09-01T09:00:00Z",
    ...overrides,
  };
}

export function page<T>(items: T[], total = items.length) {
  return { items, total, limit: 25, offset: 0 };
}
