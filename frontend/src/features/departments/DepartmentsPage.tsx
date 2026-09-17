import { Button } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";

import type { Schemas } from "../../api/types";
import { textParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useDepartments } from "../../shared/lookups/departments";
import { useUserNames } from "../../shared/lookups/users";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { FilterBar, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { DepartmentFormDialog } from "./DepartmentFormDialog";

type Department = Schemas["DepartmentRead"];

const FILTERS = { q: textParam };

export function DepartmentsPage() {
  const departments = useDepartments();
  const { nameOf } = useUserNames();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const [editing, setEditing] = useState<Department | "new" | null>(null);

  const query = filters.q.trim().toLowerCase();
  const rows = departments.data?.filter((item) => item.name.toLowerCase().includes(query));

  const columns: Column<Department>[] = [
    { key: "name", header: "Название", render: (item) => item.name },
    {
      key: "head",
      header: "Руководитель",
      render: (item) => (item.head_id === null ? "Не назначен" : nameOf(item.head_id)),
    },
  ];

  return (
    <PageContainer
      title="Отделы"
      breadcrumbs={[{ label: "Администрирование" }, { label: "Отделы" }]}
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
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Поиск по названию"
        />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={rows}
        getRowId={(item) => item.id}
        loading={departments.isLoading}
        error={departments.error}
        onRetry={() => void departments.refetch()}
        emptyText="Отделы не найдены"
        rowActions={[{ label: "Редактировать", onClick: (item) => setEditing(item) }]}
        paging={{ limit, offset, onChange: setPage }}
      />
      {editing && (
        <DepartmentFormDialog
          department={editing === "new" ? null : editing}
          nameOf={nameOf}
          onClose={() => setEditing(null)}
        />
      )}
    </PageContainer>
  );
}
