import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { useAssetIssueReasons, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAssets, useIssueAssets, useReturnAssets } from "./api";
import { AssetMultiPicker } from "./AssetMultiPicker";
import type { Asset } from "./labels";

const errorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : UNKNOWN_ERROR_MESSAGE;

/** Элемент details ошибки assets_unavailable (backend: UnavailableAsset). */
interface UnavailableAsset {
  asset_id: number;
}

/** id активов из details ошибки assets_unavailable. */
function unavailableOf(error: unknown): Set<number> {
  if (!(error instanceof ApiError) || error.code !== "assets_unavailable") return new Set();
  const details = error.details as UnavailableAsset[] | null;
  return new Set((details ?? []).map((item) => item.asset_id));
}

export function IssuePage() {
  return (
    <PageContainer
      title="Выдать / принять"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "Выдать / принять" }]}
    >
      <Stack spacing={3}>
        <IssueSection />
        <ReturnSection />
      </Stack>
    </PageContainer>
  );
}

function IssueSection() {
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const reasons = useAssetIssueReasons();
  const issue = useIssueAssets();
  const [ownerId, setOwnerId] = useState<number | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [reasonId, setReasonId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [unavailable, setUnavailable] = useState<ReadonlySet<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const submit = async () => {
    setTouched(true);
    if (ownerId === null || assets.length === 0) return;
    setError(null);
    try {
      const issued = await issue.mutateAsync({
        owner_id: ownerId,
        asset_ids: assets.map((asset) => asset.id),
        reason_id: reasonId,
        comment: comment.trim() || null,
      });
      enqueueSnackbar(`Выдано: ${issued.length}`, { variant: "success" });
      setAssets([]);
      setComment("");
      setUnavailable(new Set());
      setTouched(false);
    } catch (caught) {
      setUnavailable(unavailableOf(caught));
      setError(
        caught instanceof ApiError && caught.code === "assets_unavailable"
          ? "Часть техники уже недоступна — она выделена красным. Уберите её и повторите."
          : errorMessage(caught),
      );
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5} component="section" aria-label="Выдать">
          <Typography variant="h5" component="h2">
            Выдать
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <EntityAutocomplete
            label="Кому"
            value={ownerId}
            onChange={setOwnerId}
            fetchOptions={searchActiveUserOptions}
            queryKey={ACTIVE_USER_OPTIONS_KEY}
            labelFor={nameOf}
            error={touched && ownerId === null}
            helperText={touched && ownerId === null ? "Выберите сотрудника" : undefined}
          />
          <AssetMultiPicker
            value={assets}
            onChange={(next) => {
              setAssets(next);
              setUnavailable(new Set());
            }}
            unavailableIds={unavailable}
            error={touched && assets.length === 0 ? "Выберите технику" : undefined}
          />
          <TextField
            select
            label="Причина"
            value={reasonId === null ? "" : String(reasonId)}
            onChange={(event) =>
              setReasonId(event.target.value ? Number(event.target.value) : null)
            }
          >
            <MenuItem value="">Не указана</MenuItem>
            {(reasons.data ?? []).map((item) => (
              <MenuItem key={item.id} value={String(item.id)}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Комментарий"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            multiline
            minRows={2}
          />
          <Stack direction="row">
            <Button variant="contained" loading={issue.isPending} onClick={() => void submit()}>
              Выдать
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

function ReturnSection() {
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const locations = useLocations();
  const returnAssets = useReturnAssets();
  const [ownerId, setOwnerId] = useState<number | null>(null);
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const [locationId, setLocationId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const owned = useAssets({ ownerId, status: "in_use", limit: 100, offset: 0 }, ownerId !== null);

  const toggle = (id: number) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const submit = async () => {
    setError(null);
    try {
      const returned = await returnAssets.mutateAsync({
        asset_ids: [...selected],
        location_id: locationId,
        comment: comment.trim() || null,
      });
      enqueueSnackbar(`Принято на склад: ${returned.length}`, { variant: "success" });
      setSelected(new Set());
      setComment("");
    } catch (caught) {
      setSelected(new Set());
      setError(
        caught instanceof ApiError && caught.code === "assets_unavailable"
          ? "Список техники изменился — он обновлён. Отметьте технику заново."
          : errorMessage(caught),
      );
    }
  };

  const items = owned.data?.items ?? [];

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5} component="section" aria-label="Принять">
          <Typography variant="h5" component="h2">
            Принять
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <EntityAutocomplete
            label="От кого"
            value={ownerId}
            onChange={(id) => {
              setOwnerId(id);
              setSelected(new Set());
              setError(null);
            }}
            fetchOptions={searchActiveUserOptions}
            queryKey={ACTIVE_USER_OPTIONS_KEY}
            labelFor={nameOf}
          />
          {ownerId !== null && owned.isSuccess && items.length === 0 && (
            <Typography color="text.secondary">У сотрудника нет техники в работе</Typography>
          )}
          {owned.error && <Alert severity="error">{errorMessage(owned.error)}</Alert>}
          {items.length > 0 && (
            <Stack>
              {items.map((asset) => (
                <FormControlLabel
                  key={asset.id}
                  label={`${asset.inventory_number} — ${asset.model}`}
                  control={
                    <Checkbox checked={selected.has(asset.id)} onChange={() => toggle(asset.id)} />
                  }
                />
              ))}
            </Stack>
          )}
          <TextField
            select
            label="Локация (если меняется)"
            value={locationId === null ? "" : String(locationId)}
            onChange={(event) =>
              setLocationId(event.target.value ? Number(event.target.value) : null)
            }
          >
            <MenuItem value="">Не менять</MenuItem>
            {(locations.data ?? []).map((item) => (
              <MenuItem key={item.id} value={String(item.id)}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Комментарий"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            multiline
            minRows={2}
          />
          <Stack direction="row">
            <Button
              variant="contained"
              disabled={selected.size === 0}
              loading={returnAssets.isPending}
              onClick={() => void submit()}
            >
              Принять на склад
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
