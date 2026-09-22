import { Box, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { formatDateTime } from "../../shared/lib/format";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { useStockMovements } from "./api";
import { formatDelta, movementDetails, movementTitle, type StockMovement } from "./labels";

const PAGE_SIZE = 25;

export function StockHistory({ itemId, unit }: { itemId: number; unit: string }) {
  const [offset, setOffset] = useState(0);
  const movements = useStockMovements(itemId, PAGE_SIZE, offset);
  const columns: Column<StockMovement>[] = [
    {
      key: "created_at",
      header: "Когда",
      width: 160,
      render: (movement) => formatDateTime(movement.created_at),
    },
    {
      key: "movement",
      header: "Операция",
      render: (movement) => (
        <Stack spacing={0.5}>
          <Typography sx={{ fontWeight: 600 }}>{movementTitle(movement.movement_type)}</Typography>
          {movementDetails(movement).map((line) => (
            <Typography key={line} variant="body2" color="text.secondary">
              {line}
            </Typography>
          ))}
          {movement.comment && (
            <Box component="q" sx={{ typography: "body2" }}>
              {movement.comment}
            </Box>
          )}
        </Stack>
      ),
    },
    {
      key: "delta",
      header: "Изменение",
      render: (movement) => formatDelta(movement.delta, unit),
    },
    {
      key: "quantity_after",
      header: "Остаток после",
      render: (movement) => `${movement.quantity_after} ${unit}`,
    },
    { key: "performed_by", header: "Кто", render: (movement) => movement.performed_by_name },
  ];
  return (
    <DataTable
      columns={columns}
      rows={movements.data?.items}
      getRowId={(movement) => movement.id}
      loading={movements.isLoading}
      error={movements.error}
      onRetry={() => void movements.refetch()}
      emptyText="Движений нет"
      paging={{
        limit: PAGE_SIZE,
        offset,
        total: movements.data?.total ?? 0,
        onChange: (nextOffset) => setOffset(nextOffset),
      }}
    />
  );
}
