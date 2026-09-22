import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useAssetTypes, useLocations } from "../../shared/lookups/directories";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormSwitch } from "../../shared/ui/form/FormSwitch";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateAsset, useUpdateAsset } from "./api";
import type { Asset } from "./labels";

interface AssetFormValues {
  asset_type_id: number | null;
  inventory_number: string;
  serial_number: string;
  model: string;
  location_id: number | null;
  accepted_at: string;
  purchased_at: string;
  warranty_until: string;
  initial_cost: string;
  needs_review: boolean;
}

const FIELDS = [
  "asset_type_id",
  "inventory_number",
  "serial_number",
  "model",
  "location_id",
  "accepted_at",
  "purchased_at",
  "warranty_until",
  "initial_cost",
] as const;

const fieldForError = fieldByCode<AssetFormValues>({
  inventory_number_taken: "inventory_number",
  inventory_number_blank: "inventory_number",
  serial_number_taken: "serial_number",
  model_blank: "model",
  asset_type_invalid: "asset_type_id",
  location_invalid: "location_id",
});

const required = { required: "Обязательное поле" };
const optional = (value: string) => value.trim() || null;

/** Варианты справочника; деактивированное текущее значение добавляется, чтобы форма его показала. */
function withCurrent(
  items: { id: number; name: string }[] | undefined,
  currentId?: number,
  currentName?: string,
) {
  const options = (items ?? []).map((item) => ({ value: item.id, label: item.name }));
  if (currentId !== undefined && !options.some((option) => option.value === currentId)) {
    options.push({ value: currentId, label: currentName ?? "" });
  }
  return options;
}

function toValues(asset: Asset | null): AssetFormValues {
  return {
    asset_type_id: asset?.asset_type_id ?? null,
    inventory_number: asset?.inventory_number ?? "",
    serial_number: asset?.serial_number ?? "",
    model: asset?.model ?? "",
    location_id: asset?.location_id ?? null,
    accepted_at: asset?.accepted_at ?? new Date().toISOString().slice(0, 10),
    purchased_at: asset?.purchased_at ?? "",
    warranty_until: asset?.warranty_until ?? "",
    initial_cost: asset?.initial_cost ?? "",
    needs_review: asset?.needs_review ?? false,
  };
}

interface AssetFormDialogProps {
  /** Актив для редактирования; без него диалог создаёт новый. */
  asset: Asset | null;
  onClose: () => void;
  /** Вызывается с сохранённым активом (после создания — чтобы открыть карточку). */
  onSaved?: (asset: Asset) => void;
}

export function AssetFormDialog({ asset, onClose, onSaved }: AssetFormDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const createAsset = useCreateAsset();
  const updateAsset = useUpdateAsset();
  const types = useAssetTypes();
  const locations = useLocations();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<AssetFormValues>({ defaultValues: toValues(asset) });

  const typeOptions = withCurrent(types.data, asset?.asset_type_id, asset?.asset_type_name);
  const locationOptions = withCurrent(locations.data);

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const body = {
      asset_type_id: values.asset_type_id!,
      inventory_number: values.inventory_number,
      serial_number: optional(values.serial_number),
      model: values.model,
      accepted_at: values.accepted_at,
      purchased_at: optional(values.purchased_at),
      warranty_until: optional(values.warranty_until),
      initial_cost: optional(values.initial_cost.replace(",", ".")),
    };
    try {
      let saved: Asset;
      if (asset) {
        const changed = Object.fromEntries(
          Object.entries({ ...body, needs_review: values.needs_review }).filter(
            ([key]) => dirtyFields[key as keyof AssetFormValues],
          ),
        );
        saved = await updateAsset.mutateAsync({
          id: asset.id,
          body: { ...changed, version: asset.version },
        });
      } else {
        saved = await createAsset.mutateAsync({
          ...body,
          location_id: values.location_id!,
          needs_review: false,
        });
      }
      onSaved?.(saved);
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.code === "version_conflict") {
        enqueueSnackbar(
          "Данные изменил другой пользователь — карточка обновлена, внесите правки заново",
          {
            variant: "warning",
          },
        );
        onClose();
        return;
      }
      setFormError(applyApiErrors(error, setError, { fields: FIELDS, fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={asset ? "Редактирование техники" : "Новая техника"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={asset ? "Сохранить" : "Добавить"}
    >
      <FormSelect
        control={control}
        name="asset_type_id"
        label="Тип"
        options={typeOptions}
        rules={required}
      />
      <FormTextField
        control={control}
        name="inventory_number"
        label="Инвентарный номер"
        rules={required}
      />
      <FormTextField control={control} name="serial_number" label="Серийный номер" />
      <FormTextField control={control} name="model" label="Модель" rules={required} />
      {!asset && (
        <FormSelect
          control={control}
          name="location_id"
          label="Локация"
          options={locationOptions}
          rules={required}
        />
      )}
      <FormTextField
        control={control}
        name="accepted_at"
        label="Дата принятия к учёту"
        type="date"
        rules={required}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <FormTextField
        control={control}
        name="purchased_at"
        label="Дата покупки"
        type="date"
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <FormTextField
        control={control}
        name="warranty_until"
        label="Гарантия до"
        type="date"
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <FormTextField
        control={control}
        name="initial_cost"
        label="Стоимость, ₽"
        rules={{
          validate: (value) =>
            value.trim() === "" ||
            /^\d{1,10}([.,]\d{1,2})?$/.test(value.trim()) ||
            "Введите сумму, например 95000.00",
        }}
      />
      {asset && <FormSwitch control={control} name="needs_review" label="Требует проверки" />}
    </FormDialog>
  );
}
