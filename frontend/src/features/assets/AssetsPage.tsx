import { Button, FormControlLabel, Link as MuiLink, Switch, Typography } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { useAuth } from "../auth";
import { formatDate } from "../../shared/lib/format";
import {
  booleanParam,
  enumParam,
  idParam,
  textParam,
  useUrlFilters,
} from "../../shared/lib/useUrlFilters";
import { useAssetTypes, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { FilterBar, FilterSelect, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAssets } from "./api";
import { AssetFormDialog } from "./AssetFormDialog";
import { AssetStatusChip } from "./AssetStatusChip";
import { ASSET_STATUSES, STATUS_LABELS, type Asset } from "./labels";

const FILTERS = {
  q: textParam,
  status: enumParam(ASSET_STATUSES),
  type: idParam,
  owner: idParam,
  location: idParam,
  review: booleanParam,
};

const STATUS_OPTIONS = ASSET_STATUSES.map((status) => ({
  value: status,
  label: STATUS_LABELS[status],
}));

const SCOPE_TEXT = {
  employee: "Ваша техника",
  manager: "Техника сотрудников вашего отдела",
  admin: null,
} as const;

export function AssetsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const assets = useAssets({
    q: filters.q,
    status: filters.status,
    assetTypeId: filters.type,
    ownerId: isAdmin ? filters.owner : null,
    locationId: filters.location,
    needsReview: isAdmin ? filters.review : null,
    limit,
    offset,
  });
  const types = useAssetTypes();
  const locations = useLocations();
  const [creating, setCreating] = useState(false);

  const columns: Column<Asset>[] = [
    {
      key: "inventory_number",
      header: "Инв. номер",
      render: (asset) => (
        <MuiLink component={Link} to={`/equipment/assets/${asset.id}`}>
          {asset.inventory_number}
        </MuiLink>
      ),
    },
    { key: "type", header: "Тип", render: (asset) => asset.asset_type_name },
    { key: "model", header: "Модель", render: (asset) => asset.model },
    {
      key: "status",
      header: "Статус",
      render: (asset) => <AssetStatusChip status={asset.status} />,
    },
    { key: "owner", header: "Владелец", render: (asset) => asset.owner_name ?? "—" },
    { key: "location", header: "Локация", render: (asset) => asset.location_name },
    {
      key: "warranty",
      header: "Гарантия до",
      render: (asset) => (asset.warranty_until ? formatDate(asset.warranty_until) : "—"),
    },
  ];

  const scopeText = user ? SCOPE_TEXT[user.role] : null;

  return (
    <PageContainer
      title="Реестр техники"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "Реестр техники" }]}
      actions={
        isAdmin && (
          <Button
            variant="contained"
            startIcon={<IconPlus size={18} />}
            onClick={() => setCreating(true)}
          >
            Добавить
          </Button>
        )
      }
    >
      {scopeText && (
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          {scopeText}
        </Typography>
      )}
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Инв. номер, серийный номер, модель"
        />
        <FilterSelect
          label="Статус"
          value={filters.status}
          options={STATUS_OPTIONS}
          allLabel="Все, кроме списанных"
          onChange={(value) => setFilter("status", value)}
        />
        <FilterSelect
          label="Тип"
          value={filters.type}
          options={(types.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("type", value)}
        />
        <FilterSelect
          label="Локация"
          value={filters.location}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("location", value)}
        />
        {isAdmin && <OwnerFilter value={filters.owner} onChange={(id) => setFilter("owner", id)} />}
        {isAdmin && (
          <FormControlLabel
            label="Требует проверки"
            control={
              <Switch
                checked={filters.review === true}
                onChange={(event) => setFilter("review", event.target.checked ? true : null)}
              />
            }
          />
        )}
      </FilterBar>

      <DataTable
        columns={columns}
        rows={assets.data?.items}
        getRowId={(asset) => asset.id}
        loading={assets.isLoading}
        error={assets.error}
        onRetry={() => void assets.refetch()}
        emptyText="Техника не найдена"
        paging={{ limit, offset, total: assets.data?.total ?? 0, onChange: setPage }}
      />

      {creating && (
        <AssetFormDialog
          asset={null}
          onClose={() => setCreating(false)}
          onSaved={(asset) => void navigate(`/equipment/assets/${asset.id}`)}
        />
      )}
    </PageContainer>
  );
}

function OwnerFilter({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const { nameOf } = useUserNames();
  return (
    <EntityAutocomplete
      label="Владелец"
      value={value}
      onChange={onChange}
      fetchOptions={searchActiveUserOptions}
      queryKey={ACTIVE_USER_OPTIONS_KEY}
      labelFor={nameOf}
    />
  );
}
