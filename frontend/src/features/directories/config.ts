import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";

export const DIRECTORY_KINDS = [
  "locations",
  "asset-types",
  "stock-categories",
  "issue-reasons",
  "ticket-types",
] as const;

export type DirectoryKind = (typeof DIRECTORY_KINDS)[number];

export type Applicability = Schemas["IssueReasonApplicability"];

/** Общая форма элемента: у каждого справочника используется своё подмножество полей. */
export interface DirectoryItem {
  id: number;
  name: string;
  is_active: boolean;
  description?: string | null;
  applicability?: Applicability;
  code?: string;
  requires_approval?: boolean;
  default_assignee_id?: number | null;
}

export interface DirectoryFormValues {
  name: string;
  description: string;
  applicability: Applicability;
  code: string;
  requires_approval: boolean;
  default_assignee_id: number | null;
}

export type ExtraField =
  "description" | "applicability" | "code" | "requires_approval" | "default_assignee_id";

export interface DirectoryConfig {
  kind: DirectoryKind;
  title: string;
  extraFields: readonly ExtraField[];
  list: (includeInactive: boolean) => Promise<DirectoryItem[]>;
  create: (values: DirectoryFormValues) => Promise<DirectoryItem>;
  /** `values` — только изменённые поля формы; `code` не меняется после создания. */
  update: (
    id: number,
    values: Partial<DirectoryFormValues> & { is_active?: boolean },
  ) => Promise<DirectoryItem>;
}

const inactive = (includeInactive: boolean) => ({
  params: { query: { include_inactive: includeInactive } },
});
const item = (id: number) => ({ path: { item_id: id } });

export const DIRECTORIES: Record<DirectoryKind, DirectoryConfig> = {
  locations: {
    kind: "locations",
    title: "Локации",
    extraFields: ["description"],
    list: (all) => unwrap(api.GET("/api/directories/locations", inactive(all))),
    create: (v) =>
      unwrap(
        api.POST("/api/admin/directories/locations", {
          body: { name: v.name, description: v.description.trim() || null },
        }),
      ),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/locations/{item_id}", {
          params: item(id),
          body: {
            name: v.name,
            description: v.description === undefined ? undefined : v.description.trim() || null,
            is_active: v.is_active,
          },
        }),
      ),
  },
  "asset-types": {
    kind: "asset-types",
    title: "Типы техники",
    extraFields: [],
    list: (all) => unwrap(api.GET("/api/directories/asset-types", inactive(all))),
    create: (v) =>
      unwrap(api.POST("/api/admin/directories/asset-types", { body: { name: v.name } })),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/asset-types/{item_id}", {
          params: item(id),
          body: { name: v.name, is_active: v.is_active },
        }),
      ),
  },
  "stock-categories": {
    kind: "stock-categories",
    title: "Категории расходников",
    extraFields: [],
    list: (all) => unwrap(api.GET("/api/directories/stock-categories", inactive(all))),
    create: (v) =>
      unwrap(api.POST("/api/admin/directories/stock-categories", { body: { name: v.name } })),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/stock-categories/{item_id}", {
          params: item(id),
          body: { name: v.name, is_active: v.is_active },
        }),
      ),
  },
  "issue-reasons": {
    kind: "issue-reasons",
    title: "Причины выдачи",
    extraFields: ["applicability"],
    list: (all) => unwrap(api.GET("/api/directories/issue-reasons", inactive(all))),
    create: (v) =>
      unwrap(
        api.POST("/api/admin/directories/issue-reasons", {
          body: { name: v.name, applicability: v.applicability },
        }),
      ),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/issue-reasons/{item_id}", {
          params: item(id),
          body: { name: v.name, applicability: v.applicability, is_active: v.is_active },
        }),
      ),
  },
  "ticket-types": {
    kind: "ticket-types",
    title: "Типы заявок",
    extraFields: ["code", "requires_approval", "default_assignee_id"],
    list: (all) => unwrap(api.GET("/api/directories/ticket-types", inactive(all))),
    create: (v) =>
      unwrap(
        api.POST("/api/admin/directories/ticket-types", {
          body: {
            code: v.code,
            name: v.name,
            requires_approval: v.requires_approval,
            default_assignee_id: v.default_assignee_id,
          },
        }),
      ),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/ticket-types/{item_id}", {
          params: item(id),
          body: {
            name: v.name,
            requires_approval: v.requires_approval,
            default_assignee_id: v.default_assignee_id,
            is_active: v.is_active,
          },
        }),
      ),
  },
};

export function isDirectoryKind(value: string | undefined): value is DirectoryKind {
  return DIRECTORY_KINDS.some((kind) => kind === value);
}
