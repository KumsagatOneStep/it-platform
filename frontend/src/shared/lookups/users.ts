import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";

import { api, unwrap } from "../../api/client";
import type { EntityOption } from "../ui/EntityAutocomplete";
import { queryKeys } from "./queryKeys";

// Пользователей в компании 10–15: для подписей в админских таблицах хватает одной страницы.
const NAMES_PAGE_SIZE = 200;

/** Имена пользователей по id (только для администратора: использует /api/admin/users). */
export function useUserNames() {
  const query = useQuery({
    queryKey: [...queryKeys.users, "names"],
    queryFn: () =>
      unwrap(api.GET("/api/admin/users", { params: { query: { limit: NAMES_PAGE_SIZE } } })),
  });
  const names = useMemo(
    () => new Map(query.data?.items.map((user) => [user.id, user.full_name]) ?? []),
    [query.data],
  );
  const nameOf = useCallback((id: number) => names.get(id) ?? `Пользователь #${id}`, [names]);
  return { nameOf, isLoading: query.isLoading };
}

export const RESPONSIBLE_OPTIONS_KEY = [...queryKeys.users, "responsible-options"] as const;

/**
 * Варианты ответственного (руководитель отдела, исполнитель по умолчанию): активные Manager и Admin.
 * /api/users не подходит: требует непустой запрос и не фильтрует по роли.
 */
export async function searchResponsibleOptions(query: string): Promise<EntityOption[]> {
  const page = await unwrap(
    api.GET("/api/admin/users", {
      params: { query: { q: query.trim() || undefined, is_active: true, limit: 50 } },
    }),
  );
  return page.items
    .filter((user) => user.role !== "employee")
    .map((user) => ({ id: user.id, label: user.full_name }));
}

/** Варианты активных сотрудников любой роли (для выдачи техники; только администратор). */
export async function searchActiveUserOptions(query: string): Promise<EntityOption[]> {
  const page = await unwrap(
    api.GET("/api/admin/users", {
      params: { query: { q: query.trim() || undefined, is_active: true, limit: 50 } },
    }),
  );
  return page.items.map((user) => ({ id: user.id, label: user.full_name }));
}

export const ACTIVE_USER_OPTIONS_KEY = [...queryKeys.users, "active-options"] as const;
