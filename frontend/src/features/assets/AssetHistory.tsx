import { Box, Stack, Typography } from "@mui/material";

import { useState } from "react";

import { formatDateTime } from "../../shared/lib/format";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { useAssetEvents } from "./api";
import { eventChanges, eventTitle, type AssetEvent } from "./labels";

const PAGE_SIZE = 25;

const columns: Column<AssetEvent>[] = [
  {
    key: "created_at",
    header: "Когда",
    width: 160,
    render: (event) => formatDateTime(event.created_at),
  },
  {
    key: "event",
    header: "Событие",
    render: (event) => (
      <Stack spacing={0.5}>
        <Typography sx={{ fontWeight: 600 }}>{eventTitle(event)}</Typography>
        {eventChanges(event).map((line) => (
          <Typography key={line} variant="body2" color="text.secondary">
            {line}
          </Typography>
        ))}
        {event.reason_name && (
          <Typography variant="body2" color="text.secondary">
            Причина: {event.reason_name}
          </Typography>
        )}
        {event.comment && (
          <Box component="q" sx={{ typography: "body2" }}>
            {event.comment}
          </Box>
        )}
      </Stack>
    ),
  },
  { key: "performed_by", header: "Кто", render: (event) => event.performed_by_name },
];

export function AssetHistory({ assetId }: { assetId: number }) {
  const [offset, setOffset] = useState(0);
  const events = useAssetEvents(assetId, PAGE_SIZE, offset);
  return (
    <DataTable
      columns={columns}
      rows={events.data?.items}
      getRowId={(event) => event.id}
      loading={events.isLoading}
      error={events.error}
      onRetry={() => void events.refetch()}
      emptyText="Событий нет"
      paging={{
        limit: PAGE_SIZE,
        offset,
        total: events.data?.total ?? 0,
        onChange: (nextOffset) => setOffset(nextOffset),
      }}
    />
  );
}
