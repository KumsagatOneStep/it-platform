import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas, UserRole } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";

export interface UserListParams {
  q: string;
  role: UserRole | null;
  departmentId: number | null;
  isActive: boolean | null;
  limit: number;
  offset: number;
}

export function useAdminUsers(params: UserListParams) {
  return useQuery({
    queryKey: [...queryKeys.users, "admin-list", params],
    queryFn: () =>
      unwrap(
        api.GET("/api/admin/users", {
          params: {
            query: {
              q: params.q.trim() || undefined,
              role: params.role ?? undefined,
              department_id: params.departmentId ?? undefined,
              is_active: params.isActive ?? undefined,
              limit: params.limit,
              offset: params.offset,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

function useUsersMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.users }),
  });
}

export function useCreateUser() {
  return useUsersMutation((body: Schemas["UserCreate"]) =>
    unwrap(api.POST("/api/admin/users", { body })),
  );
}

export function useUpdateUser() {
  return useUsersMutation(({ id, body }: { id: number; body: Schemas["UserUpdate"] }) =>
    unwrap(api.PATCH("/api/admin/users/{user_id}", { params: { path: { user_id: id } }, body })),
  );
}

export function useSetUserActive() {
  return useUsersMutation(({ id, active }: { id: number; active: boolean }) => {
    const params = { params: { path: { user_id: id } } };
    return active
      ? unwrap(api.POST("/api/admin/users/{user_id}/activate", params))
      : unwrap(api.POST("/api/admin/users/{user_id}/deactivate", params));
  });
}

export function useIssueTemporaryPassword() {
  return useUsersMutation((id: number) =>
    unwrap(
      api.POST("/api/admin/users/{user_id}/temporary-password", {
        params: { path: { user_id: id } },
      }),
    ),
  );
}

export function useUnlockLogin() {
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.POST("/api/admin/users/{user_id}/unlock-login", { params: { path: { user_id: id } } }),
      ),
  });
}
