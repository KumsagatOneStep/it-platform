import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useLocations, useStockCategories } from "../../shared/lookups/directories";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormSwitch } from "../../shared/ui/form/FormSwitch";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateStockItem, useUpdateStockItem } from "./api";
import type { StockItem } from "./labels";

interface StockItemFormValues {
  name: string;
  stock_category_id: number | null;
  unit: string;
  location_id: number | null;
  min_quantity: string;
  is_active: boolean;
}

const FIELDS = ["name", "stock_category_id", "unit", "location_id", "min_quantity"] as const;

const fieldForError = fieldByCode<StockItemFormValues>({
  stock_item_name_taken: "name",
  name_blank: "name",
  unit_blank: "unit",
  category_invalid: "stock_category_id",
  location_invalid: "location_id",
});

const required = { required: "Обязательное поле" };

function toValues(item: StockItem | null): StockItemFormValues {
  return {
    name: item?.name ?? "",
    stock_category_id: item?.stock_category_id ?? null,
    unit: item?.unit ?? "шт",
    location_id: item?.location_id ?? null,
    min_quantity: item && item.min_quantity > 0 ? String(item.min_quantity) : "",
    is_active: item?.is_active ?? true,
  };
}

/** Варианты справочника; деактивированное текущее значение добавляется, чтобы форма его показала. */
function withCurrent(
  items: { id: number; name: string }[] | undefined,
  currentId?: number,
  currentName?: string,
) {
  const options = (items ?? []).map((entry) => ({ value: entry.id, label: entry.name }));
  if (currentId !== undefined && !options.some((option) => option.value === currentId)) {
    options.push({ value: currentId, label: currentName ?? "" });
  }
  return options;
}

interface StockItemFormDialogProps {
  /** Позиция для редактирования; без неё диалог создаёт новую. */
  item: StockItem | null;
  onClose: () => void;
  onSaved?: (item: StockItem) => void;
}

export function StockItemFormDialog({ item, onClose, onSaved }: StockItemFormDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const createItem = useCreateStockItem();
  const updateItem = useUpdateStockItem();
  const categories = useStockCategories();
  const locations = useLocations();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<StockItemFormValues>({ defaultValues: toValues(item) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const body = {
      name: values.name,
      stock_category_id: values.stock_category_id!,
      unit: values.unit,
      min_quantity: values.min_quantity.trim() === "" ? 0 : Number(values.min_quantity),
    };
    try {
      let saved: StockItem;
      if (item) {
        const changed = Object.fromEntries(
          Object.entries({ ...body, is_active: values.is_active }).filter(
            ([key]) => dirtyFields[key as keyof StockItemFormValues],
          ),
        );
        saved = await updateItem.mutateAsync({
          id: item.id,
          body: { ...changed, version: item.version },
        });
      } else {
        saved = await createItem.mutateAsync({ ...body, location_id: values.location_id! });
      }
      onSaved?.(saved);
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.code === "version_conflict") {
        enqueueSnackbar(
          "Данные изменил другой пользователь — карточка обновлена, внесите правки заново",
          { variant: "warning" },
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
      title={item ? "Редактирование позиции" : "Новая позиция"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={item ? "Сохранить" : "Добавить"}
    >
      <FormTextField control={control} name="name" label="Наименование" rules={required} />
      <FormSelect
        control={control}
        name="stock_category_id"
        label="Категория"
        options={withCurrent(categories.data, item?.stock_category_id, item?.category_name)}
        rules={required}
      />
      <FormTextField control={control} name="unit" label="Единица измерения" rules={required} />
      {!item && (
        <FormSelect
          control={control}
          name="location_id"
          label="Склад"
          options={withCurrent(locations.data)}
          rules={required}
        />
      )}
      <FormTextField
        control={control}
        name="min_quantity"
        label="Минимальный остаток"
        helperText="Ниже или равно — позиция подсвечивается. Пусто — без контроля"
        rules={{
          validate: (value) =>
            value.trim() === "" || /^\d{1,7}$/.test(value.trim()) || "Целое число от 0",
        }}
      />
      {item && <FormSwitch control={control} name="is_active" label="Активна" />}
    </FormDialog>
  );
}
