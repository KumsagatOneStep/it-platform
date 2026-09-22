import { Alert } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useAssetIssueReasons, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useAssetOperation, type OperationBody } from "./api";
import { OPERATION_LABELS, type Asset, type Operation } from "./labels";

interface OperationFormValues {
  owner_id: number | null;
  reason_id: number | null;
  location_id: number | null;
  comment: string;
}

type FieldMode = "required" | "optional";

/** Поля формы для каждой операции (п. 3 спецификации). */
const OPERATION_FIELDS: Record<
  Operation,
  Partial<Record<"owner_id" | "reason_id" | "location_id", FieldMode>>
> = {
  issue: { owner_id: "required", reason_id: "optional" },
  return: { location_id: "optional" },
  reserve: {},
  unreserve: {},
  to_repair: {},
  repair_to_owner: {},
  repair_to_stock: { location_id: "optional" },
  write_off: { reason_id: "required" },
  move: { location_id: "required" },
};

const fieldForError = fieldByCode<OperationFormValues>({
  recipient_invalid: "owner_id",
  reason_invalid: "reason_id",
  reason_required: "reason_id",
  location_invalid: "location_id",
});

function buildBody(operation: Operation, values: OperationFormValues): OperationBody {
  const comment = values.comment.trim() || null;
  switch (operation) {
    case "issue":
      return { operation, owner_id: values.owner_id!, reason_id: values.reason_id, comment };
    case "return":
    case "repair_to_stock":
      return { operation, location_id: values.location_id, comment };
    case "write_off":
      return { operation, reason_id: values.reason_id, comment };
    case "move":
      return { operation, location_id: values.location_id!, comment };
    default:
      return { operation, comment };
  }
}

interface AssetOperationDialogProps {
  asset: Asset;
  operation: Operation;
  onClose: () => void;
}

export function AssetOperationDialog({ asset, operation, onClose }: AssetOperationDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const mutation = useAssetOperation();
  const reasons = useAssetIssueReasons();
  const locations = useLocations();
  const { nameOf } = useUserNames();
  const [formError, setFormError] = useState<string | null>(null);
  const fields = OPERATION_FIELDS[operation];
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting },
  } = useForm<OperationFormValues>({
    defaultValues: { owner_id: null, reason_id: null, location_id: null, comment: "" },
  });
  const rulesFor = (field: keyof typeof fields) =>
    fields[field] === "required" ? { required: "Обязательное поле" } : undefined;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await mutation.mutateAsync({ id: asset.id, body: buildBody(operation, values) });
      enqueueSnackbar(`${OPERATION_LABELS[operation]}: готово`, { variant: "success" });
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.code === "operation_not_allowed") {
        enqueueSnackbar("Статус техники изменился — данные обновлены", { variant: "warning" });
        onClose();
        return;
      }
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["owner_id", "reason_id", "location_id", "comment"],
          fieldForError,
        }),
      );
    }
  });

  return (
    <FormDialog
      open
      title={`${OPERATION_LABELS[operation]}: ${asset.inventory_number}`}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={OPERATION_LABELS[operation]}
    >
      {operation === "write_off" && (
        <Alert severity="warning">
          Списание необратимо: техника больше не будет доступна для операций.
        </Alert>
      )}
      {fields.owner_id && (
        <FormAutocomplete
          control={control}
          name="owner_id"
          label="Сотрудник"
          fetchOptions={searchActiveUserOptions}
          queryKey={ACTIVE_USER_OPTIONS_KEY}
          labelFor={nameOf}
          rules={rulesFor("owner_id")}
        />
      )}
      {fields.reason_id && (
        <FormSelect
          control={control}
          name="reason_id"
          label="Причина"
          emptyLabel={fields.reason_id === "optional" ? "Не указана" : undefined}
          options={(reasons.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          rules={rulesFor("reason_id")}
        />
      )}
      {fields.location_id && (
        <FormSelect
          control={control}
          name="location_id"
          label={fields.location_id === "optional" ? "Локация (если меняется)" : "Локация"}
          emptyLabel={fields.location_id === "optional" ? "Не менять" : undefined}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          rules={rulesFor("location_id")}
        />
      )}
      <FormTextField control={control} name="comment" label="Комментарий" multiline minRows={2} />
    </FormDialog>
  );
}
