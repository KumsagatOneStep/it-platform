import { Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { localDateIso } from "../../shared/lib/format";
import { useLocations, useStockIssueReasons } from "../../shared/lookups/directories";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useStockOperation, type StockOperationBody } from "./api";
import { formatDelta, STOCK_OPERATION_LABELS, type StockItem, type StockOperation } from "./labels";
import { StockItemPicker } from "./StockItemPicker";

interface OperationFormValues {
  item: StockItem | null;
  quantity: string;
  actual_quantity: string;
  document_date: string;
  reason_id: number | null;
  to_location_id: number | null;
  comment: string;
}

const fieldForError = fieldByCode<OperationFormValues>({
  document_date_in_future: "document_date",
  reason_required: "reason_id",
  reason_invalid: "reason_id",
  comment_required: "comment",
  adjustment_no_change: "actual_quantity",
  same_location: "to_location_id",
  location_invalid: "to_location_id",
});

const FIELDS = [
  "quantity",
  "actual_quantity",
  "document_date",
  "reason_id",
  "to_location_id",
  "comment",
] as const;

const required = { required: "Обязательное поле" };
const INTEGER = /^\d{1,7}$/;

function buildBody(operation: StockOperation, values: OperationFormValues): StockOperationBody {
  const comment = values.comment.trim() || null;
  const quantity = Number(values.quantity);
  switch (operation) {
    case "receipt":
      return { operation, quantity, document_date: values.document_date || null, comment };
    case "write_off":
      return { operation, quantity, reason_id: values.reason_id, comment };
    case "adjustment":
      return { operation, actual_quantity: Number(values.actual_quantity), comment };
    case "transfer":
      return { operation, quantity, to_location_id: values.to_location_id!, comment };
  }
}

interface StockOperationDialogProps {
  /** Позиция; null — выбирается в диалоге (приход со страницы списка). */
  item: StockItem | null;
  operation: StockOperation;
  onClose: () => void;
}

export function StockOperationDialog({ item, operation, onClose }: StockOperationDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const mutation = useStockOperation();
  const reasons = useStockIssueReasons();
  const locations = useLocations();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    watch,
    formState: { isSubmitting },
  } = useForm<OperationFormValues>({
    defaultValues: {
      item,
      quantity: "",
      actual_quantity: "",
      document_date: localDateIso(),
      reason_id: null,
      to_location_id: null,
      comment: "",
    },
  });
  const current = watch("item");
  const unit = current?.unit ?? "шт";
  const actual = watch("actual_quantity");
  const label = STOCK_OPERATION_LABELS[operation];
  const outgoing = operation === "write_off" || operation === "transfer";

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await mutation.mutateAsync({ id: values.item!.id, body: buildBody(operation, values) });
      enqueueSnackbar(`${label}: готово`, { variant: "success" });
      onClose();
    } catch (error) {
      if (
        error instanceof ApiError &&
        (error.code === "insufficient_stock" || error.code === "stock_item_inactive")
      ) {
        enqueueSnackbar("Остаток изменился — данные обновлены", { variant: "warning" });
        onClose();
        return;
      }
      setFormError(applyApiErrors(error, setError, { fields: FIELDS, fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={item ? `${label}: ${item.name}` : label}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={label}
    >
      {!item && (
        <Controller
          control={control}
          name="item"
          rules={{ required: "Выберите позицию" }}
          render={({ field, fieldState }) => (
            <StockItemPicker
              value={field.value}
              onChange={field.onChange}
              error={fieldState.error?.message}
            />
          )}
        />
      )}
      {operation === "adjustment" ? (
        <>
          {current && (
            <Typography color="text.secondary">
              Учётный остаток: {current.quantity} {unit}
            </Typography>
          )}
          <FormTextField
            control={control}
            name="actual_quantity"
            label={`Фактический остаток, ${unit}`}
            rules={{
              required: "Обязательное поле",
              validate: (value) => INTEGER.test(value.trim()) || "Целое число от 0",
            }}
          />
          {current && INTEGER.test(actual.trim()) && Number(actual) !== current.quantity && (
            <Typography>
              Изменение: {formatDelta(Number(actual) - current.quantity, unit)}
            </Typography>
          )}
        </>
      ) : (
        <FormTextField
          control={control}
          name="quantity"
          label={`Количество, ${unit}`}
          rules={{
            required: "Обязательное поле",
            validate: (value) => {
              if (!INTEGER.test(value.trim()) || Number(value) < 1) return "Целое число от 1";
              if (outgoing && current && Number(value) > current.quantity) {
                return `Не больше остатка: ${current.quantity} ${unit}`;
              }
              return true;
            },
          }}
        />
      )}
      {operation === "receipt" && (
        <FormTextField
          control={control}
          name="document_date"
          label="Дата документа"
          type="date"
          rules={required}
          slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: localDateIso() } }}
        />
      )}
      {operation === "write_off" && (
        <FormSelect
          control={control}
          name="reason_id"
          label="Причина"
          options={(reasons.data ?? []).map((reason) => ({ value: reason.id, label: reason.name }))}
          rules={required}
        />
      )}
      {operation === "transfer" && (
        <FormSelect
          control={control}
          name="to_location_id"
          label="Куда"
          options={(locations.data ?? [])
            .filter((location) => location.id !== current?.location_id)
            .map((location) => ({ value: location.id, label: location.name }))}
          rules={required}
        />
      )}
      <FormTextField
        control={control}
        name="comment"
        label="Комментарий"
        multiline
        minRows={2}
        rules={operation === "adjustment" ? required : undefined}
      />
    </FormDialog>
  );
}
