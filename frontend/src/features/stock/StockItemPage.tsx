import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Menu,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { IconChevronDown, IconPencil } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import { useParams } from "react-router";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { FullScreenLoader } from "../../shared/ui/FullScreenLoader";
import { PageContainer } from "../../shared/ui/PageContainer";
import { StatusPage } from "../../shared/ui/StatusPage";
import { useStockItem } from "./api";
import {
  STOCK_OPERATION_LABELS,
  STOCK_OPERATIONS,
  type StockItem,
  type StockOperation,
} from "./labels";
import { StockHistory } from "./StockHistory";
import { StockItemFormDialog } from "./StockItemFormDialog";
import { StockOperationDialog } from "./StockOperationDialog";
import { StockQuantityChip } from "./StockQuantityChip";

function StockItemNotFound() {
  return <StatusPage code={404} title="Позиция не найдена" text="Возможно, ссылка устарела." />;
}

export function StockItemPage() {
  const { id } = useParams();
  const itemId = Number(id);
  if (!Number.isInteger(itemId) || itemId <= 0) return <StockItemNotFound />;
  return <StockItemScreen key={itemId} itemId={itemId} />;
}

function StockItemScreen({ itemId }: { itemId: number }) {
  const item = useStockItem(itemId);
  if (item.isLoading) return <FullScreenLoader />;
  if (item.error) {
    if (item.error instanceof ApiError && item.error.status === 404) return <StockItemNotFound />;
    return (
      <Alert severity="error">
        {item.error instanceof ApiError ? item.error.message : UNKNOWN_ERROR_MESSAGE}
      </Alert>
    );
  }
  return item.data ? <StockItemCard item={item.data} /> : null;
}

function StockItemCard({ item }: { item: StockItem }) {
  const [tab, setTab] = useState<"info" | "history">("info");
  const [editing, setEditing] = useState(false);
  const [operation, setOperation] = useState<StockOperation | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  return (
    <PageContainer
      title={item.name}
      breadcrumbs={[
        { label: "Склад и техника" },
        { label: "Расходники", to: "/equipment/stock" },
        { label: item.name },
      ]}
      actions={
        <>
          <Button
            variant="outlined"
            startIcon={<IconPencil size={18} />}
            onClick={() => setEditing(true)}
          >
            Редактировать
          </Button>
          {item.is_active && (
            <Button
              variant="contained"
              endIcon={<IconChevronDown size={18} />}
              onClick={(event) => setMenuAnchor(event.currentTarget)}
            >
              Действия
            </Button>
          )}
          <Menu
            anchorEl={menuAnchor}
            open={Boolean(menuAnchor)}
            onClose={() => setMenuAnchor(null)}
          >
            {STOCK_OPERATIONS.map((item) => (
              <MenuItem
                key={item}
                onClick={() => {
                  setMenuAnchor(null);
                  setOperation(item);
                }}
              >
                {STOCK_OPERATION_LABELS[item]}
              </MenuItem>
            ))}
          </Menu>
        </>
      }
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, alignItems: "center" }}>
        <StockQuantityChip item={item} />
        {item.is_low && <Typography color="error.main">Низкий остаток</Typography>}
        {!item.is_active && <Chip size="small" label="Неактивна" />}
      </Stack>
      <Tabs value={tab} onChange={(_, value: "info" | "history") => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="info" label="Информация" />
        <Tab value="history" label="История" />
      </Tabs>
      {tab === "info" ? (
        <StockItemInfo item={item} />
      ) : (
        <StockHistory itemId={item.id} unit={item.unit} />
      )}

      {editing && <StockItemFormDialog item={item} onClose={() => setEditing(false)} />}
      {operation && (
        <StockOperationDialog
          item={item}
          operation={operation}
          onClose={() => setOperation(null)}
        />
      )}
    </PageContainer>
  );
}

function StockItemInfo({ item }: { item: StockItem }) {
  const rows: [string, ReactNode][] = [
    ["Категория", item.category_name],
    ["Склад", item.location_name],
    ["Единица измерения", item.unit],
    ["Остаток", `${item.quantity} ${item.unit}`],
    ["Минимальный остаток", item.min_quantity > 0 ? `${item.min_quantity} ${item.unit}` : "—"],
    ["Статус", item.is_active ? "Активна" : "Неактивна"],
  ];
  return (
    <Card variant="outlined">
      <CardContent>
        <Grid container spacing={2}>
          {rows.map(([label, value]) => (
            <Grid key={label} size={{ xs: 12, sm: 6, md: 4 }}>
              <Typography variant="body2" color="text.secondary">
                {label}
              </Typography>
              <Typography>{value}</Typography>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}
