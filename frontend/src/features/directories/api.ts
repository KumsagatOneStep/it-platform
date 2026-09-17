import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../shared/lookups/queryKeys";
import type { DirectoryConfig, DirectoryFormValues } from "./config";

export function useDirectoryItems(config: DirectoryConfig, includeInactive: boolean) {
  return useQuery({
    queryKey: [...queryKeys.directories, config.kind, { includeInactive }],
    queryFn: () => config.list(includeInactive),
  });
}

export function useSaveDirectoryItem(config: DirectoryConfig) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      values,
    }: {
      id: number | null;
      values: Partial<DirectoryFormValues> & { is_active?: boolean };
    }) => (id === null ? config.create(values as DirectoryFormValues) : config.update(id, values)),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...queryKeys.directories, config.kind] }),
  });
}
