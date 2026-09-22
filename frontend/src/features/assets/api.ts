import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";
import type { AssetStatus } from "./labels";

export interface AssetListParams {
  q?: string;
  status?: AssetStatus | null;
  assetTypeId?: number | null;
  ownerId?: number | null;
  locationId?: number | null;
  needsReview?: boolean | null;
  limit: number;
  offset: number;
}

export function fetchAssets(params: AssetListParams) {
  return unwrap(
    api.GET("/api/assets", {
      params: {
        query: {
          q: params.q?.trim() || undefined,
          status: params.status ? [params.status] : undefined,
          asset_type_id: params.assetTypeId ?? undefined,
          owner_id: params.ownerId ?? undefined,
          location_id: params.locationId ?? undefined,
          needs_review: params.needsReview ?? undefined,
          limit: params.limit,
          offset: params.offset,
        },
      },
    }),
  );
}

export function useAssets(params: AssetListParams, enabled = true) {
  return useQuery({
    queryKey: [...queryKeys.assets, "list", params],
    queryFn: () => fetchAssets(params),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useAsset(id: number) {
  return useQuery({
    queryKey: [...queryKeys.assets, "detail", id],
    queryFn: () =>
      unwrap(api.GET("/api/assets/{asset_id}", { params: { path: { asset_id: id } } })),
  });
}

export function useAssetEvents(id: number, limit: number, offset: number) {
  return useQuery({
    queryKey: [...queryKeys.assets, "events", id, { limit, offset }],
    queryFn: () =>
      unwrap(
        api.GET("/api/assets/{asset_id}/events", {
          params: { path: { asset_id: id }, query: { limit, offset } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Мутация, после которой перезапрашиваются все данные техники (реестр, карточка, история). */
function useAssetsMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.assets }),
  });
}

export function useCreateAsset() {
  return useAssetsMutation((body: Schemas["AssetCreate"]) =>
    unwrap(api.POST("/api/assets", { body })),
  );
}

export function useUpdateAsset() {
  return useAssetsMutation(({ id, body }: { id: number; body: Schemas["AssetUpdate"] }) =>
    unwrap(api.PATCH("/api/assets/{asset_id}", { params: { path: { asset_id: id } }, body })),
  );
}

export type OperationBody =
  | Schemas["IssueOperation"]
  | Schemas["ReturnOperation"]
  | Schemas["StatusOperation"]
  | Schemas["WriteOffOperation"]
  | Schemas["MoveOperation"];

export function useAssetOperation() {
  return useAssetsMutation(({ id, body }: { id: number; body: OperationBody }) =>
    unwrap(
      api.POST("/api/assets/{asset_id}/operations", { params: { path: { asset_id: id } }, body }),
    ),
  );
}

export function useIssueAssets() {
  return useAssetsMutation((body: Schemas["AssetIssueRequest"]) =>
    unwrap(api.POST("/api/assets/issue", { body })),
  );
}

export function useReturnAssets() {
  return useAssetsMutation((body: Schemas["AssetReturnRequest"]) =>
    unwrap(api.POST("/api/assets/return", { body })),
  );
}
