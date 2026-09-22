import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import { queryKeys } from "../../shared/lookups/queryKeys";
import type { JournalGroup, JournalKind } from "./labels";

export interface JournalParams {
  dateFrom: string | null;
  dateTo: string | null;
  kind: JournalKind | null;
  group: JournalGroup | null;
  personId: number | null;
  performedBy: number | null;
  locationId: number | null;
  limit: number;
  offset: number;
}

export function useJournal(params: JournalParams) {
  return useQuery({
    queryKey: [...queryKeys.movements, "journal", params],
    queryFn: () =>
      unwrap(
        api.GET("/api/equipment/movements", {
          params: {
            query: {
              date_from: params.dateFrom ?? undefined,
              date_to: params.dateTo ?? undefined,
              kind: params.kind ?? undefined,
              group: params.group ? [params.group] : undefined,
              person_id: params.personId ?? undefined,
              performed_by: params.performedBy ?? undefined,
              location_id: params.locationId ?? undefined,
              limit: params.limit,
              offset: params.offset,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
