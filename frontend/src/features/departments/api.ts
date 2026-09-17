import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";

function useDepartmentsMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.departments }),
  });
}

export function useCreateDepartment() {
  return useDepartmentsMutation((body: Schemas["DepartmentCreate"]) =>
    unwrap(api.POST("/api/admin/departments", { body })),
  );
}

export function useUpdateDepartment() {
  return useDepartmentsMutation(({ id, body }: { id: number; body: Schemas["DepartmentUpdate"] }) =>
    unwrap(
      api.PATCH("/api/admin/departments/{department_id}", {
        params: { path: { department_id: id } },
        body,
      }),
    ),
  );
}
