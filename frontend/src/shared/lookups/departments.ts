import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import { queryKeys } from "./queryKeys";

export function useDepartments() {
  return useQuery({
    queryKey: [...queryKeys.departments, "list"],
    queryFn: () => unwrap(api.GET("/api/departments")),
  });
}
