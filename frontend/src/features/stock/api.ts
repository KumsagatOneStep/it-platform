import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";

export interface StockListParams {
  q?: string;
  categoryId?: number | null;
  locationId?: number | null;
  lowStock?: boolean;
  /** Только позиции с остатком > 0. */
  inStock?: boolean;
  includeInactive?: boolean;
  limit: number;
  offset: number;
}

export function fetchStockItems(params: StockListParams) {
  return unwrap(
    api.GET("/api/stock-items", {
      params: {
        query: {
          q: params.q?.trim() || undefined,
          category_id: params.categoryId ?? undefined,
          location_id: params.locationId ?? undefined,
          low_stock: params.lowStock || undefined,
          in_stock: params.inStock || undefined,
          include_inactive: params.includeInactive || undefined,
          limit: params.limit,
          offset: params.offset,
        },
      },
    }),
  );
}

export function useStockItems(params: StockListParams) {
  return useQuery({
    queryKey: [...queryKeys.stock, "list", params],
    queryFn: () => fetchStockItems(params),
    placeholderData: keepPreviousData,
  });
}

export function useStockItem(id: number) {
  return useQuery({
    queryKey: [...queryKeys.stock, "detail", id],
    queryFn: () =>
      unwrap(api.GET("/api/stock-items/{item_id}", { params: { path: { item_id: id } } })),
  });
}

export function useStockMovements(id: number, limit: number, offset: number) {
  return useQuery({
    queryKey: [...queryKeys.stock, "movements", id, { limit, offset }],
    queryFn: () =>
      unwrap(
        api.GET("/api/stock-items/{item_id}/movements", {
          params: { path: { item_id: id }, query: { limit, offset } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Мутация, после которой перезапрашиваются расходники и журнал движений. */
function useStockMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.stock }),
        queryClient.invalidateQueries({ queryKey: queryKeys.movements }),
      ]);
    },
  });
}

export function useCreateStockItem() {
  return useStockMutation((body: Schemas["StockItemCreate"]) =>
    unwrap(api.POST("/api/stock-items", { body })),
  );
}

export function useUpdateStockItem() {
  return useStockMutation(({ id, body }: { id: number; body: Schemas["StockItemUpdate"] }) =>
    unwrap(api.PATCH("/api/stock-items/{item_id}", { params: { path: { item_id: id } }, body })),
  );
}

export type StockOperationBody =
  | Schemas["StockReceiptOperation"]
  | Schemas["StockWriteOffOperation"]
  | Schemas["StockAdjustmentOperation"]
  | Schemas["StockTransferOperation"];

export function useStockOperation() {
  return useStockMutation(({ id, body }: { id: number; body: StockOperationBody }) =>
    unwrap(
      api.POST("/api/stock-items/{item_id}/operations", {
        params: { path: { item_id: id } },
        body,
      }),
    ),
  );
}
