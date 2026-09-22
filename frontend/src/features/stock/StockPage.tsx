import {
  Button,
  FormControlLabel,
  Link as MuiLink,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { booleanParam, idParam, textParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useLocations, useStockCategories } from "../../shared/lookups/directories";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { FilterBar, FilterSelect, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useStockItems } from "./api";
import type { StockItem } from "./labels";
import { StockItemFormDialog } from "./StockItemFormDialog";
import { StockQuantityChip } from "./StockQuantityChip";

const FILTERS = {
  q: textParam,
  category: idParam,
  location: idParam,
  low: booleanParam,
  inactive: booleanParam,
};

const columns: Column<StockItem>[] = [
  {
    key: "name",
    header: "Наименование",
    render: (item) => (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <MuiLink component={Link} to={`/equipment/stock/${item.id}`}>
          {item.name}
        </MuiLink>
        {!item.is_active && (
          <Typography variant="body2" color="text.secondary">
            неактивна
          </Typography>
        )}
      </Stack>
    ),
  },
  { key: "category", header: "Категория", render: (item) => item.category_name },
  { key: "location", header: "Склад", render: (item) => item.location_name },
  { key: "quantity", header: "Остаток", render: (item) => <StockQuantityChip item={item} /> },
  {
    key: "min_quantity",
    header: "Минимум",
    render: (item) => (item.min_quantity > 0 ? `${item.min_quantity} ${item.unit}` : "—"),
  },
];

export function StockPage() {
  const navigate = useNavigate();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const items = useStockItems({
    q: filters.q,
    categoryId: filters.category,
    locationId: filters.location,
    lowStock: filters.low === true,
    includeInactive: filters.inactive === true,
    limit,
    offset,
  });
  const categories = useStockCategories();
  const locations = useLocations();
  const [creating, setCreating] = useState(false);

  const toggle = (key: "low" | "inactive", label: string) => (
    <FormControlLabel
      label={label}
      control={
        <Switch
          checked={filters[key] === true}
          onChange={(event) => setFilter(key, event.target.checked ? true : null)}
        />
      }
    />
  );

  return (
    <PageContainer
      title="Расходники"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "Расходники" }]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setCreating(true)}
        >
          Добавить позицию
        </Button>
      }
    >
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Наименование"
        />
        <FilterSelect
          label="Категория"
          value={filters.category}
          options={(categories.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("category", value)}
        />
        <FilterSelect
          label="Склад"
          value={filters.location}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("location", value)}
        />
        {toggle("low", "Только низкий остаток")}
        {toggle("inactive", "Показать неактивные")}
      </FilterBar>

      <DataTable
        columns={columns}
        rows={items.data?.items}
        getRowId={(item) => item.id}
        loading={items.isLoading}
        error={items.error}
        onRetry={() => void items.refetch()}
        emptyText="Позиции не найдены"
        paging={{ limit, offset, total: items.data?.total ?? 0, onChange: setPage }}
      />

      {creating && (
        <StockItemFormDialog
          item={null}
          onClose={() => setCreating(false)}
          onSaved={(item) => void navigate(`/equipment/stock/${item.id}`)}
        />
      )}
    </PageContainer>
  );
}
