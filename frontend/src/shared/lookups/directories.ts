import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "./queryKeys";

/** Активные элементы справочников для выпадающих списков форм. */
export function useLocations() {
  return useQuery({
    queryKey: [...queryKeys.directories, "locations", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/locations")),
  });
}

export function useAssetTypes() {
  return useQuery({
    queryKey: [...queryKeys.directories, "asset-types", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/asset-types")),
  });
}

export function useStockCategories() {
  return useQuery({
    queryKey: [...queryKeys.directories, "stock-categories", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/stock-categories")),
  });
}

/** Состав операции: есть ли в ней техника и расходники. */
export interface ReasonScope {
  assets: boolean;
  stock: boolean;
}

/** Причина покрывает весь состав операции (backend: checks._reason_fits). */
export function reasonFits(
  applicability: Schemas["IssueReasonApplicability"],
  scope: ReasonScope,
): boolean {
  if (applicability === "both") return true;
  if (scope.assets && scope.stock) return false;
  return applicability === (scope.assets ? "assets" : "stock");
}

/** Все активные причины выдачи; фильтр по составу — reasonFits. */
export function useIssueReasons() {
  return useQuery({
    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
  });
}

/** Причины выдачи, применимые к технике (applicability assets или both). */
export function useAssetIssueReasons() {
  return useQuery({
    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
    select: (items) =>
      items.filter((item) => reasonFits(item.applicability, { assets: true, stock: false })),
  });
}

/** Причины, применимые к расходникам (applicability stock или both). */
export function useStockIssueReasons() {
  return useQuery({
    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
    select: (items) =>
      items.filter((item) => reasonFits(item.applicability, { assets: false, stock: true })),
  });
}
