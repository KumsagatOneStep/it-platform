import { useState } from "react";
import { useForm } from "react-hook-form";

import type { Schemas } from "../../api/types";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { RESPONSIBLE_OPTIONS_KEY, searchResponsibleOptions } from "../../shared/lookups/users";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateDepartment, useUpdateDepartment } from "./api";

interface DepartmentFormValues {
  name: string;
  head_id: number | null;
}

const fieldForError = fieldByCode<DepartmentFormValues>({
  department_name_taken: "name",
  department_name_blank: "name",
  head_not_found: "head_id",
  head_invalid_role: "head_id",
});

interface DepartmentFormDialogProps {
  department: Schemas["DepartmentRead"] | null;
  nameOf: (userId: number) => string;
  onClose: () => void;
}

export function DepartmentFormDialog({ department, nameOf, onClose }: DepartmentFormDialogProps) {
  const createDepartment = useCreateDepartment();
  const updateDepartment = useUpdateDepartment();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<DepartmentFormValues>({
    defaultValues: { name: department?.name ?? "", head_id: department?.head_id ?? null },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (department) {
        const body: Schemas["DepartmentUpdate"] = {};
        if (dirtyFields.name) body.name = values.name;
        if (dirtyFields.head_id) body.head_id = values.head_id;
        await updateDepartment.mutateAsync({ id: department.id, body });
      } else {
        await createDepartment.mutateAsync(values);
      }
      onClose();
    } catch (error) {
      setFormError(applyApiErrors(error, setError, { fields: ["name", "head_id"], fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={department ? "Редактирование отдела" : "Новый отдел"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={department ? "Сохранить" : "Создать"}
    >
      <FormTextField
        control={control}
        name="name"
        label="Название"
        rules={{ validate: (value) => value.trim() !== "" || "Введите название" }}
      />
      <FormAutocomplete
        control={control}
        name="head_id"
        label="Руководитель"
        fetchOptions={searchResponsibleOptions}
        queryKey={RESPONSIBLE_OPTIONS_KEY}
        labelFor={nameOf}
      />
    </FormDialog>
  );
}
