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

export function makeAsset(overrides: Partial<Schemas["AssetRead"]> = {}): Schemas["AssetRead"] {
  return {
    id: 100,
    asset_type_id: 1,
    asset_type_name: "Ноутбук",
    inventory_number: "INV-001",
    serial_number: "SN-001",
    model: "Lenovo ThinkPad T14",
    status: "in_stock",
    location_id: 5,
    location_name: "Склад",
    owner_id: null,
    owner_name: null,
    accepted_at: "2026-01-15",
    purchased_at: null,
    warranty_until: "2028-01-15",
    initial_cost: "95000.00",
    needs_review: false,
    version: 1,
    created_at: "2026-09-01T09:00:00Z",
    updated_at: "2026-09-01T09:00:00Z",
    allowed_operations: ["issue", "reserve", "to_repair", "write_off", "move"],
    ...overrides,
  };
}

export function makeAssetEvent(
  overrides: Partial<Schemas["AssetEventRead"]> = {},
): Schemas["AssetEventRead"] {
  return {
    id: 1,
    event_type: "created",
    operation: null,
    from_owner_id: null,
    from_owner_name: null,
    to_owner_id: null,
    to_owner_name: null,
    from_status: null,
    to_status: "in_stock",
    from_location_id: null,
    from_location_name: null,
    to_location_id: 5,
    to_location_name: "Склад",
    reason_id: null,
    reason_name: null,
    changes: null,
    comment: null,
    performed_by: 1,
    performed_by_name: "Иванов Иван",
    created_at: "2026-09-01T09:00:00Z",
    ...overrides,
  };
}
