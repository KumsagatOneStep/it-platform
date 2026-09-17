import { Button, Chip, FormControlLabel, Switch, Tab, Tabs } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";

import { ApiError } from "../../api/errors";
import { APPLICABILITY_LABELS } from "../../shared/lib/format";
import { booleanParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useUserNames } from "../../shared/lookups/users";
import { DataTable, type Column, type RowAction } from "../../shared/ui/DataTable";
import { FilterBar } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useDirectoryItems, useSaveDirectoryItem } from "./api";
import {
  DIRECTORIES,
  DIRECTORY_KINDS,
  isDirectoryKind,
  type DirectoryConfig,
  type DirectoryItem,
} from "./config";
import { DirectoryFormDialog } from "./DirectoryFormDialog";

const FILTERS = { inactive: booleanParam };

export function DirectoriesPage() {
  const { kind } = useParams();
  if (!isDirectoryKind(kind)) return <Navigate to="/admin/directories/locations" replace />;
  return <DirectoryScreen key={kind} config={DIRECTORIES[kind]} />;
}

function DirectoryScreen({ config }: { config: DirectoryConfig }) {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const includeInactive = filters.inactive === true;
  const items = useDirectoryItems(config, includeInactive);
  const save = useSaveDirectoryItem(config);
  const [editing, setEditing] = useState<DirectoryItem | "new" | null>(null);

  const has = (field: (typeof config.extraFields)[number]) => config.extraFields.includes(field);

  const setActive = async (item: DirectoryItem, active: boolean) => {
    try {
      await save.mutateAsync({ id: item.id, values: { is_active: active } });
      enqueueSnackbar(active ? "Элемент активирован" : "Элемент деактивирован", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar(error instanceof ApiError ? error.message : "Не удалось выполнить запрос", {
        variant: "error",
      });
    }
  };

  const columns: Column<DirectoryItem>[] = [
    ...(has("code")
      ? [{ key: "code", header: "Код", render: (item: DirectoryItem) => item.code }]
      : []),
    { key: "name", header: "Название", render: (item) => item.name },
    ...(has("description")
      ? [
          {
            key: "description",
            header: "Описание",
            render: (item: DirectoryItem) => item.description ?? "—",
          },
        ]
      : []),
    ...(has("applicability")
      ? [
          {
            key: "applicability",
            header: "Применимость",
            render: (item: DirectoryItem) =>
              item.applicability ? APPLICABILITY_LABELS[item.applicability] : "—",
          },
        ]
      : []),
    ...(has("requires_approval")
      ? [
          {
            key: "requires_approval",
            header: "Согласование",
            render: (item: DirectoryItem) =>
              item.requires_approval ? "Требуется" : "Не требуется",
          },
        ]
      : []),
    ...(has("default_assignee_id")
      ? [
          {
            key: "default_assignee_id",
            header: "Исполнитель по умолчанию",
            render: (item: DirectoryItem) =>
              item.default_assignee_id ? nameOf(item.default_assignee_id) : "—",
          },
        ]
      : []),
    {
      key: "status",
      header: "Статус",
      render: (item) => (
        <Chip
          size="small"
          label={item.is_active ? "Активен" : "Неактивен"}
          color={item.is_active ? "success" : "default"}
        />
      ),
    },
  ];

  const rowActions: RowAction<DirectoryItem>[] = [
    { label: "Редактировать", onClick: (item) => setEditing(item) },
    {
      label: "Деактивировать",
      color: "error",
      hidden: (item) => !item.is_active,
      onClick: (item) => void setActive(item, false),
    },
    {
      label: "Активировать",
      hidden: (item) => item.is_active,
      onClick: (item) => void setActive(item, true),
    },
  ];

  return (
    <PageContainer
      title="Справочники"
      breadcrumbs={[
        { label: "Администрирование" },
        { label: "Справочники" },
        { label: config.title },
      ]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setEditing("new")}
        >
          Добавить
        </Button>
      }
    >
      <Tabs
        value={config.kind}
        onChange={(_, next: string) => void navigate(`/admin/directories/${next}`)}
        variant="scrollable"
        sx={{ mb: 2 }}
      >
        {DIRECTORY_KINDS.map((kind) => (
          <Tab key={kind} value={kind} label={DIRECTORIES[kind].title} />
        ))}
      </Tabs>
      <FilterBar>
        <FormControlLabel
          label="Показывать неактивные"
          control={
            <Switch
              checked={includeInactive}
              onChange={(event) => setFilter("inactive", event.target.checked ? true : null)}
            />
          }
        />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={items.data}
        getRowId={(item) => item.id}
        loading={items.isLoading}
        error={items.error}
        onRetry={() => void items.refetch()}
        emptyText="Элементов нет"
        rowActions={rowActions}
        paging={{ limit, offset, onChange: setPage }}
      />
      {editing && (
        <DirectoryFormDialog
          config={config}
          item={editing === "new" ? null : editing}
          nameOf={nameOf}
          onClose={() => setEditing(null)}
        />
      )}
    </PageContainer>
  );
}
