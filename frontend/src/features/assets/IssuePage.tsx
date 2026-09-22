import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  Stack,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useAssetIssueReasons, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { PageContainer } from "../../shared/ui/PageContainer";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
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

interface IssueFormValues {
  owner_id: number | null;
  asset_ids: Asset[];
  reason_id: number | null;
  comment: string;
}

const issueFieldForError = fieldByCode<IssueFormValues>({
  recipient_invalid: "owner_id",
  reason_invalid: "reason_id",
  reason_required: "reason_id",
});

function IssueSection() {
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const reasons = useAssetIssueReasons();
  const issue = useIssueAssets();
  const [unavailable, setUnavailable] = useState<ReadonlySet<number>>(new Set());
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    reset,
    formState: { isSubmitting },
  } = useForm<IssueFormValues>({
    defaultValues: { owner_id: null, asset_ids: [], reason_id: null, comment: "" },
  });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const issued = await issue.mutateAsync({
        owner_id: values.owner_id!,
        asset_ids: values.asset_ids.map((asset) => asset.id),
        reason_id: values.reason_id,
        comment: values.comment.trim() || null,
      });
      enqueueSnackbar(`Выдано: ${issued.length}`, { variant: "success" });
      reset({ owner_id: values.owner_id, asset_ids: [], reason_id: null, comment: "" });
      setUnavailable(new Set());
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "assets_unavailable") {
        setUnavailable(unavailableOf(caught));
        setFormError(
          "Часть техники уже недоступна — она выделена красным. Уберите её и повторите.",
        );
        return;
      }
      setFormError(
        applyApiErrors(caught, setError, {
          fields: ["owner_id", "asset_ids", "reason_id", "comment"],
          fieldForError: issueFieldForError,
        }),
      );
    }
  });

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5} component="section" aria-label="Выдать">
          <Typography variant="h5" component="h2">
            Выдать
          </Typography>
          {formError && <Alert severity="error">{formError}</Alert>}
          <FormAutocomplete
            control={control}
            name="owner_id"
            label="Кому"
            fetchOptions={searchActiveUserOptions}
            queryKey={ACTIVE_USER_OPTIONS_KEY}
            labelFor={nameOf}
            rules={{ required: "Выберите сотрудника" }}
          />
          <Controller
            control={control}
            name="asset_ids"
            rules={{ validate: (value) => value.length > 0 || "Выберите технику" }}
            render={({ field, fieldState }) => (
              <AssetMultiPicker
                value={field.value}
                onChange={(next) => {
                  field.onChange(next);
                  setUnavailable(new Set());
                }}
                unavailableIds={unavailable}
                error={fieldState.error?.message}
              />
            )}
          />
          <FormSelect
            control={control}
            name="reason_id"
            label="Причина"
            emptyLabel="Не указана"
            options={(reasons.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          />
          <FormTextField
            control={control}
            name="comment"
            label="Комментарий"
            multiline
            minRows={2}
          />
          <Stack direction="row">
            <Button
              variant="contained"
              loading={issue.isPending || isSubmitting}
              onClick={() => void submit()}
            >
              Выдать
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

interface ReturnFormValues {
  location_id: number | null;
  comment: string;
}

const returnFieldForError = fieldByCode<ReturnFormValues>({
  location_invalid: "location_id",
});

function ReturnSection() {
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const locations = useLocations();
  const returnAssets = useReturnAssets();
  const [ownerId, setOwnerId] = useState<number | null>(null);
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const [formError, setFormError] = useState<string | null>(null);
  const owned = useAssets({ ownerId, status: "in_use", limit: 100, offset: 0 }, ownerId !== null);
  const {
    control,
    handleSubmit,
    setError,
    reset,
    formState: { isSubmitting },
  } = useForm<ReturnFormValues>({ defaultValues: { location_id: null, comment: "" } });

  const toggle = (id: number) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const returned = await returnAssets.mutateAsync({
        asset_ids: [...selected],
        location_id: values.location_id,
        comment: values.comment.trim() || null,
      });
      enqueueSnackbar(`Принято на склад: ${returned.length}`, { variant: "success" });
      setSelected(new Set());
      reset({ location_id: null, comment: "" });
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "assets_unavailable") {
        setSelected(new Set());
        setFormError("Список техники изменился — он обновлён. Отметьте технику заново.");
        return;
      }
      setFormError(
        applyApiErrors(caught, setError, {
          fields: ["location_id", "comment"],
          fieldForError: returnFieldForError,
        }),
      );
    }
  });

  const items = owned.data?.items ?? [];

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5} component="section" aria-label="Принять">
          <Typography variant="h5" component="h2">
            Принять
          </Typography>
          {formError && <Alert severity="error">{formError}</Alert>}
          <EntityAutocomplete
            label="От кого"
            value={ownerId}
            onChange={(id) => {
              setOwnerId(id);
              setSelected(new Set());
              setFormError(null);
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
          <FormSelect
            control={control}
            name="location_id"
            label="Локация (если меняется)"
            emptyLabel="Не менять"
            options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          />
          <FormTextField
            control={control}
            name="comment"
            label="Комментарий"
            multiline
            minRows={2}
          />
          <Stack direction="row">
            <Button
              variant="contained"
              disabled={selected.size === 0}
              loading={returnAssets.isPending || isSubmitting}
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
