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

import {
  StockLinesField,
  stockLineError,
  type StockLineValue,
  type UnavailableLine,
} from "../stock";
import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import {
  reasonFits,
  useIssueReasons,
  useLocations,
  type ReasonScope,
} from "../../shared/lookups/directories";
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
import { useAssets, useCheckout, useReturnAssets } from "./api";
import { AssetMultiPicker } from "./AssetMultiPicker";
import type { Asset } from "./labels";

const errorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : UNKNOWN_ERROR_MESSAGE;

/** Backend принимает до 50 активов и до 50 строк расходников за раз (checkout/return). */
const MAX_BULK_SELECTION = 50;
const BULK_LIMIT_MESSAGE = `Не больше ${MAX_BULK_SELECTION} единиц за раз`;

/** details ошибки checkout_unavailable (backend: CheckoutUnavailable). */
interface CheckoutUnavailable {
  assets: { asset_id: number }[];
  stock: { stock_item_id: number; available: number | null; is_active: boolean | null }[];
}

interface Unavailable {
  assets: ReadonlySet<number>;
  /** id позиции → остаток на сервере и активность. */
  stock: ReadonlyMap<number, UnavailableLine>;
}

const NOTHING_UNAVAILABLE: Unavailable = { assets: new Set(), stock: new Map() };

/** Недоступные активы и строки расходников из details ошибки checkout_unavailable. */
function unavailableOf(error: ApiError): Unavailable {
  const details = error.details as CheckoutUnavailable | null;
  return {
    assets: new Set((details?.assets ?? []).map((item) => item.asset_id)),
    stock: new Map(
      (details?.stock ?? []).map((line) => [
        line.stock_item_id,
        { available: line.available, isActive: line.is_active },
      ]),
    ),
  };
}

/** Состав выдачи для фильтра причин; пустая выдача — как техника (прежнее поведение формы). */
function scopeOf(assets: Asset[], lines: StockLineValue[]): ReasonScope {
  const stock = lines.length > 0;
  return { assets: assets.length > 0 || !stock, stock };
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
  stock_lines: StockLineValue[];
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
  const reasons = useIssueReasons();
  const issue = useCheckout();
  const [unavailable, setUnavailable] = useState<Unavailable>(NOTHING_UNAVAILABLE);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    setValue,
    getValues,
    watch,
    reset,
    formState: { isSubmitting, submitCount },
  } = useForm<IssueFormValues>({
    defaultValues: { owner_id: null, asset_ids: [], stock_lines: [], reason_id: null, comment: "" },
  });
  const scope = scopeOf(watch("asset_ids"), watch("stock_lines"));
  const reasonOptions = (reasons.data ?? []).filter((reason) =>
    reasonFits(reason.applicability, scope),
  );

  /** После смены состава выдачи сбрасывает причину, которая к нему больше не подходит. */
  const dropUnfitReason = (assets: Asset[], lines: StockLineValue[]) => {
    const reason = reasons.data?.find((item) => item.id === getValues("reason_id"));
    if (reason && !reasonFits(reason.applicability, scopeOf(assets, lines))) {
      setValue("reason_id", null);
    }
  };

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const issued = await issue.mutateAsync({
        recipient_id: values.owner_id!,
        asset_ids: values.asset_ids.map((asset) => asset.id),
        stock_lines: values.stock_lines.map((line) => ({
          stock_item_id: line.item!.id,
          quantity: Number(line.quantity),
        })),
        reason_id: values.reason_id,
        comment: values.comment.trim() || null,
      });
      enqueueSnackbar(`Выдано позиций: ${issued.assets.length + issued.stock_items.length}`, {
        variant: "success",
      });
      reset({
        owner_id: values.owner_id,
        asset_ids: [],
        stock_lines: [],
        reason_id: null,
        comment: "",
      });
      setUnavailable(NOTHING_UNAVAILABLE);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "checkout_unavailable") {
        setUnavailable(unavailableOf(caught));
        setFormError(
          "Часть техники или расходников уже недоступна — они выделены красным. Исправьте и повторите.",
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
            rules={{
              validate: (value, form) =>
                value.length > 0 ||
                form.stock_lines.length > 0 ||
                "Выберите технику или расходники",
            }}
            render={({ field, fieldState }) => (
              <AssetMultiPicker
                value={field.value}
                onChange={(next) => {
                  if (next.length > MAX_BULK_SELECTION) {
                    setFormError(BULK_LIMIT_MESSAGE);
                    return;
                  }
                  field.onChange(next);
                  dropUnfitReason(next, getValues("stock_lines"));
                  setUnavailable(NOTHING_UNAVAILABLE);
                  setFormError(null);
                }}
                unavailableIds={unavailable.assets}
                error={fieldState.error?.message}
              />
            )}
          />
          <Controller
            control={control}
            name="stock_lines"
            rules={{
              validate: (lines) =>
                lines.every((line) => stockLineError(line) === null) ||
                "Проверьте строки расходников",
            }}
            render={({ field, fieldState }) => (
              <Stack spacing={1}>
                <StockLinesField
                  value={field.value}
                  onChange={(next) => {
                    field.onChange(next);
                    dropUnfitReason(getValues("asset_ids"), next);
                    setUnavailable(NOTHING_UNAVAILABLE);
                    setFormError(null);
                  }}
                  unavailable={unavailable.stock}
                  showErrors={submitCount > 0}
                  maxLines={MAX_BULK_SELECTION}
                />
                {fieldState.error && (
                  <Typography variant="body2" color="error">
                    {fieldState.error.message}
                  </Typography>
                )}
              </Stack>
            )}
          />
          <FormSelect
            control={control}
            name="reason_id"
            label="Причина"
            emptyLabel="Не указана"
            options={reasonOptions.map((item) => ({ value: item.id, label: item.name }))}
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
      if (next.has(id)) {
        next.delete(id);
        setFormError(null);
        return next;
      }
      if (next.size >= MAX_BULK_SELECTION) {
        setFormError(BULK_LIMIT_MESSAGE);
        return current;
      }
      next.add(id);
      setFormError(null);
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

  // keepPreviousData у useAssets держит список прежнего сотрудника, пока грузится новый
  // (или пока owner не выбран вовсе) — без этой проверки его можно отметить и вернуть по чужому id.
  const items = ownerId !== null && !owned.isPlaceholderData ? (owned.data?.items ?? []) : [];
  const showEmpty =
    ownerId !== null && owned.isSuccess && !owned.isPlaceholderData && items.length === 0;

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
          {showEmpty && (
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
