import {
  Alert,
  Button,
  Card,
  CardContent,
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
import { useAuth } from "../auth";
import { formatDate } from "../../shared/lib/format";
import { FullScreenLoader } from "../../shared/ui/FullScreenLoader";
import { PageContainer } from "../../shared/ui/PageContainer";
import { StatusPage } from "../../shared/ui/StatusPage";
import { useAsset } from "./api";
import { AssetFormDialog } from "./AssetFormDialog";
import { AssetHistory } from "./AssetHistory";
import { AssetOperationDialog } from "./AssetOperationDialog";
import { AssetStatusChip } from "./AssetStatusChip";
import { OPERATION_LABELS, type Asset, type Operation } from "./labels";

function AssetNotFound() {
  return (
    <StatusPage
      code={404}
      title="Техника не найдена"
      text="Возможно, она не входит в вашу область видимости или ссылка устарела."
    />
  );
}

export function AssetPage() {
  const { id } = useParams();
  const assetId = Number(id);
  if (!Number.isInteger(assetId) || assetId <= 0) return <AssetNotFound />;
  return <AssetScreen key={assetId} assetId={assetId} />;
}

function AssetScreen({ assetId }: { assetId: number }) {
  const asset = useAsset(assetId);
  if (asset.isLoading) return <FullScreenLoader />;
  if (asset.error) {
    if (asset.error instanceof ApiError && asset.error.status === 404) return <AssetNotFound />;
    return (
      <Alert severity="error">
        {asset.error instanceof ApiError ? asset.error.message : UNKNOWN_ERROR_MESSAGE}
      </Alert>
    );
  }
  return asset.data ? <AssetCard asset={asset.data} /> : null;
}

function AssetCard({ asset }: { asset: Asset }) {
  const [tab, setTab] = useState<"info" | "history">("info");
  const [editing, setEditing] = useState(false);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <PageContainer
      title={`${asset.inventory_number} — ${asset.model}`}
      breadcrumbs={[
        { label: "Склад и техника" },
        { label: "Реестр техники", to: "/equipment/assets" },
        { label: asset.inventory_number },
      ]}
      actions={
        isAdmin && (
          <>
            {asset.status !== "written_off" && (
              <Button
                variant="outlined"
                startIcon={<IconPencil size={18} />}
                onClick={() => setEditing(true)}
              >
                Редактировать
              </Button>
            )}
            {asset.allowed_operations.length > 0 && (
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
              {asset.allowed_operations.map((item) => (
                <MenuItem
                  key={item}
                  onClick={() => {
                    setMenuAnchor(null);
                    setOperation(item);
                  }}
                  sx={item === "write_off" ? { color: "error.main" } : undefined}
                >
                  {OPERATION_LABELS[item]}
                </MenuItem>
              ))}
            </Menu>
          </>
        )
      }
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, alignItems: "center" }}>
        <AssetStatusChip status={asset.status} />
        {asset.needs_review && <Typography color="warning.main">Требует проверки</Typography>}
      </Stack>
      <Tabs value={tab} onChange={(_, value: "info" | "history") => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="info" label="Информация" />
        <Tab value="history" label="История" />
      </Tabs>
      {tab === "info" ? <AssetInfo asset={asset} /> : <AssetHistory assetId={asset.id} />}

      {editing && <AssetFormDialog asset={asset} onClose={() => setEditing(false)} />}
      {operation && (
        <AssetOperationDialog
          asset={asset}
          operation={operation}
          onClose={() => setOperation(null)}
        />
      )}
    </PageContainer>
  );
}

function AssetInfo({ asset }: { asset: Asset }) {
  const date = (value: string | null) => (value ? formatDate(value) : "—");
  const rows: [string, ReactNode][] = [
    ["Тип", asset.asset_type_name],
    ["Инвентарный номер", asset.inventory_number],
    ["Серийный номер", asset.serial_number ?? "—"],
    ["Модель", asset.model],
    ["Владелец", asset.owner_name ?? "—"],
    ["Локация", asset.location_name],
    ["Дата принятия к учёту", date(asset.accepted_at)],
    ["Дата покупки", date(asset.purchased_at)],
    ["Гарантия до", date(asset.warranty_until)],
    ["Стоимость", asset.initial_cost ? `${asset.initial_cost} ₽` : "—"],
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
