import { useState } from "react";
import { useForm } from "react-hook-form";

import type { ApiError } from "../../api/errors";
import { applyApiErrors } from "../../shared/lib/applyApiErrors";
import { APPLICABILITY_LABELS } from "../../shared/lib/format";
import { RESPONSIBLE_OPTIONS_KEY, searchResponsibleOptions } from "../../shared/lookups/users";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormSwitch } from "../../shared/ui/form/FormSwitch";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useSaveDirectoryItem } from "./api";
import type { Applicability, DirectoryConfig, DirectoryFormValues, DirectoryItem } from "./config";

const APPLICABILITY_OPTIONS = (Object.keys(APPLICABILITY_LABELS) as Applicability[]).map(
  (value) => ({
    value,
    label: APPLICABILITY_LABELS[value],
  }),
);

const FIELDS = [
  "name",
  "description",
  "applicability",
  "code",
  "requires_approval",
  "default_assignee_id",
] as const;

function fieldForError(error: ApiError): (typeof FIELDS)[number] | undefined {
  switch (error.code) {
    case "name_blank":
      return "name";
    case "code_blank":
      return "code";
    case "invalid_default_assignee":
    case "reference_not_found":
      return "default_assignee_id";
    case "already_exists": {
      const constraint = (error.details as { constraint?: string } | null)?.constraint ?? "";
      return constraint.endsWith("_code") ? "code" : "name";
    }
    default:
      return undefined;
  }
}

interface DirectoryFormDialogProps {
  config: DirectoryConfig;
  item: DirectoryItem | null;
  nameOf: (userId: number) => string;
  onClose: () => void;
}

export function DirectoryFormDialog({ config, item, nameOf, onClose }: DirectoryFormDialogProps) {
  const save = useSaveDirectoryItem(config);
  const [formError, setFormError] = useState<string | null>(null);
  const has = (field: (typeof config.extraFields)[number]) => config.extraFields.includes(field);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<DirectoryFormValues>({
    defaultValues: {
      name: item?.name ?? "",
      description: item?.description ?? "",
      applicability: item?.applicability ?? "both",
      code: item?.code ?? "",
      requires_approval: item?.requires_approval ?? false,
      default_assignee_id: item?.default_assignee_id ?? null,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const changed = item
      ? Object.fromEntries(
          FIELDS.filter((field) => field !== "code" && dirtyFields[field]).map((field) => [
            field,
            values[field],
          ]),
        )
      : values;
    try {
      await save.mutateAsync({ id: item?.id ?? null, values: changed });
      onClose();
    } catch (error) {
      setFormError(applyApiErrors(error, setError, { fields: FIELDS, fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={item ? `${config.title}: редактирование` : `${config.title}: новый элемент`}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={item ? "Сохранить" : "Создать"}
    >
      {has("code") && (
        <FormTextField
          control={control}
          name="code"
          label="Код"
          disabled={Boolean(item)}
          helperText="Задаётся при создании и не меняется"
          rules={{ validate: (value) => value.trim() !== "" || "Введите код" }}
        />
      )}
      <FormTextField
        control={control}
        name="name"
        label="Название"
        rules={{ validate: (value) => value.trim() !== "" || "Введите название" }}
      />
      {has("description") && (
        <FormTextField
          control={control}
          name="description"
          label="Описание"
          multiline
          minRows={2}
        />
      )}
      {has("applicability") && (
        <FormSelect
          control={control}
          name="applicability"
          label="Применимость"
          options={APPLICABILITY_OPTIONS}
        />
      )}
      {has("requires_approval") && (
        <FormSwitch control={control} name="requires_approval" label="Требует согласования" />
      )}
      {has("default_assignee_id") && (
        <FormAutocomplete
          control={control}
          name="default_assignee_id"
          label="Исполнитель по умолчанию"
          fetchOptions={searchResponsibleOptions}
          queryKey={RESPONSIBLE_OPTIONS_KEY}
          labelFor={nameOf}
        />
      )}
    </FormDialog>
  );
}
