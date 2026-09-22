import { Box, Link as MuiLink, Stack, TextField, Typography } from "@mui/material";
import { Link } from "react-router";

import { formatDateTime } from "../../shared/lib/format";
import { dateParam, enumParam, idParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useLocations } from "../../shared/lookups/directories";
import { searchUserOptions, USER_OPTIONS_KEY, useUserNames } from "../../shared/lookups/users";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { FilterBar, FilterSelect } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { formatDelta } from "../stock";
import { useJournal } from "./api";
import {
  entryDetails,
  entryLocation,
  entryTitle,
  GROUP_LABELS,
  JOURNAL_GROUPS,
  JOURNAL_KINDS,
  KIND_LABELS,
  objectLink,
  type JournalEntry,
} from "./labels";

const FILTERS = {
  from: dateParam,
  to: dateParam,
  kind: enumParam(JOURNAL_KINDS),
  group: enumParam(JOURNAL_GROUPS),
  person: idParam,
  performer: idParam,
  location: idParam,
};

const columns: Column<JournalEntry>[] = [
  {
    key: "created_at",
    header: "Когда",
    width: 150,
    render: (entry) => formatDateTime(entry.created_at),
  },
  {
    key: "operation",
    header: "Операция",
    render: (entry) => (
      <Stack spacing={0.5}>
        <Typography sx={{ fontWeight: 600 }}>{entryTitle(entry)}</Typography>
        {entryDetails(entry).map((line) => (
          <Typography key={line} variant="body2" color="text.secondary">
            {line}
          </Typography>
        ))}
        {entry.comment && (
          <Box component="q" sx={{ typography: "body2" }}>
            {entry.comment}
          </Box>
        )}
      </Stack>
    ),
  },
  {
    key: "object",
    header: "Объект",
    render: (entry) => (
      <MuiLink component={Link} to={objectLink(entry)}>
        {entry.object_label}
      </MuiLink>
    ),
  },
  {
    key: "delta",
    header: "Количество",
    render: (entry) =>
      entry.delta !== null && entry.unit !== null ? formatDelta(entry.delta, entry.unit) : "—",
  },
  { key: "location", header: "Склад / локация", render: entryLocation },
  { key: "performed_by", header: "Кто", render: (entry) => entry.performed_by_name },
];

export function MovementsPage() {
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const journal = useJournal({
    dateFrom: filters.from,
    dateTo: filters.to,
    kind: filters.kind,
    group: filters.group,
    personId: filters.person,
    performedBy: filters.performer,
    locationId: filters.location,
    limit,
    offset,
  });
  const locations = useLocations();
  const { nameOf } = useUserNames();

  const dateField = (key: "from" | "to", label: string) => (
    <TextField
      size="small"
      type="date"
      label={label}
      value={filters[key] ?? ""}
      onChange={(event) => setFilter(key, event.target.value || null)}
      slotProps={{ inputLabel: { shrink: true } }}
    />
  );

  return (
    <PageContainer
      title="История движений"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "История движений" }]}
    >
      <FilterBar>
        {dateField("from", "С")}
        {dateField("to", "По")}
        <FilterSelect
          label="Вид"
          value={filters.kind}
          options={JOURNAL_KINDS.map((kind) => ({ value: kind, label: KIND_LABELS[kind] }))}
          onChange={(value) => setFilter("kind", value)}
        />
        <FilterSelect
          label="Операция"
          value={filters.group}
          options={JOURNAL_GROUPS.map((group) => ({ value: group, label: GROUP_LABELS[group] }))}
          onChange={(value) => setFilter("group", value)}
        />
      </FilterBar>
      <FilterBar>
        <EntityAutocomplete
          label="Сотрудник"
          value={filters.person}
          onChange={(id) => setFilter("person", id)}
          fetchOptions={searchUserOptions}
          queryKey={USER_OPTIONS_KEY}
          labelFor={nameOf}
        />
        <EntityAutocomplete
          label="Кто выполнил"
          value={filters.performer}
          onChange={(id) => setFilter("performer", id)}
          fetchOptions={searchUserOptions}
          queryKey={USER_OPTIONS_KEY}
          labelFor={nameOf}
        />
        <FilterSelect
          label="Склад / локация"
          value={filters.location}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("location", value)}
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={journal.data?.items}
        getRowId={(entry) => `${entry.kind}-${entry.id}`}
        loading={journal.isLoading}
        error={journal.error}
        onRetry={() => void journal.refetch()}
        emptyText="Движений не найдено"
        paging={{ limit, offset, total: journal.data?.total ?? 0, onChange: setPage }}
      />
    </PageContainer>
  );
}
