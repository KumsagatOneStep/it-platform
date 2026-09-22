import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
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

/** Причины выдачи, применимые к технике (applicability assets или both). */
export function useAssetIssueReasons() {
  return useQuery({
    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
    select: (items) => items.filter((item) => item.applicability !== "stock"),
  });
}
