import { useState } from "react";
import { useForm } from "react-hook-form";

import type { Schemas, UserRole } from "../../api/types";
import { useAuth } from "../auth";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { ROLE_LABELS } from "../../shared/lib/format";
import { useDepartments } from "../../shared/lookups/departments";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateUser, useUpdateUser } from "./api";

export const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as UserRole[]).map((role) => ({
  value: role,
  label: ROLE_LABELS[role],
}));

interface UserFormValues {
  full_name: string;
  email: string;
  role: UserRole;
  department_id: number | null;
}

const fieldForError = fieldByCode<UserFormValues>({
  email_taken: "email",
  full_name_blank: "full_name",
  department_not_found: "department_id",
});

interface UserFormDialogProps {
  /** Пользователь для редактирования; без него диалог создаёт нового. */
  user: Schemas["UserRead"] | null;
  onClose: () => void;
  onCreated: (result: Schemas["UserCreatedResponse"]) => void;
  onBlocked: (error: unknown) => boolean;
}

export function UserFormDialog({ user, onClose, onCreated, onBlocked }: UserFormDialogProps) {
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const departments = useDepartments();
  const { user: currentUser, reloadUser } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<UserFormValues>({
    defaultValues: {
      full_name: user?.full_name ?? "",
      email: user?.email ?? "",
      role: user?.role ?? "employee",
      department_id: user?.department_id ?? null,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (user) {
        const body: Schemas["UserUpdate"] = {};
        if (dirtyFields.full_name) body.full_name = values.full_name;
        if (dirtyFields.role) body.role = values.role;
        if (dirtyFields.department_id) body.department_id = values.department_id;
        await updateUser.mutateAsync({ id: user.id, body });
        if (currentUser?.id === user.id) await reloadUser();
        onClose();
      } else {
        onCreated(await createUser.mutateAsync(values));
      }
    } catch (error) {
      if (onBlocked(error)) return;
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["full_name", "email", "role", "department_id"],
          fieldForError,
        }),
      );
    }
  });

  return (
    <FormDialog
      open
      title={user ? "Редактирование пользователя" : "Новый пользователь"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={user ? "Сохранить" : "Создать"}
    >
      <FormTextField
        control={control}
        name="full_name"
        label="ФИО"
        rules={{ validate: (value) => value.trim() !== "" || "Введите ФИО" }}
      />
      <FormTextField
        control={control}
        name="email"
        label="Email"
        type="email"
        disabled={Boolean(user)}
        rules={{ required: "Введите email" }}
      />
      <FormSelect control={control} name="role" label="Роль" options={ROLE_OPTIONS} />
      <FormSelect
        control={control}
        name="department_id"
        label="Отдел"
        emptyLabel="Без отдела"
        options={(departments.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
      />
    </FormDialog>
  );
}
