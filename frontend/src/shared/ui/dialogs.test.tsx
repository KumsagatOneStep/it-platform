import { screen } from "@testing-library/react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { renderWithProviders } from "../../test/render";
import { applyApiErrors, fieldByCode } from "../lib/applyApiErrors";
import { BlockersDialog } from "./BlockersDialog";
import { FormDialog } from "./FormDialog";
import { FormSelect } from "./form/FormSelect";
import { FormTextField } from "./form/FormTextField";

interface Values {
  name: string;
  role: "employee" | "admin" | null;
}

function DepartmentForm({ submit }: { submit: (values: Values) => Promise<void> }) {
  const { control, handleSubmit, setError } = useForm<Values>({
    defaultValues: { name: "", role: null },
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true);
    setFormError(null);
    try {
      await submit(values);
    } catch (error) {
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["name", "role"],
          fieldForError: fieldByCode<Values>({ department_name_taken: "name" }),
        }),
      );
    } finally {
      setSubmitting(false);
    }
  });
  return (
    <FormDialog
      open
      title="Новый отдел"
      submitting={submitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={() => undefined}
    >
      <FormTextField control={control} name="name" label="Название" />
      <FormSelect
        control={control}
        name="role"
        label="Роль"
        emptyLabel="Не выбрана"
        options={[
          { value: "employee", label: "Сотрудник" },
          { value: "admin", label: "Администратор" },
        ]}
      />
    </FormDialog>
  );
}

test("FormDialog показывает ошибку backend под полем и сообщение над формой", async () => {
  const submit = vi
    .fn<(values: Values) => Promise<void>>()
    .mockRejectedValueOnce(
      new ApiError({
        status: 409,
        code: "department_name_taken",
        message: "Отдел с таким названием уже существует",
      }),
    )
    .mockRejectedValueOnce(new ApiError({ status: 409, code: "other", message: "Что-то не так" }));
  const { user } = renderWithProviders(<DepartmentForm submit={submit} />);

  await user.type(screen.getByLabelText("Название"), "ИТ");
  await user.click(screen.getByLabelText("Роль"));
  await user.click(await screen.findByRole("option", { name: "Администратор" }));
  await user.click(screen.getByRole("button", { name: "Сохранить" }));

  expect(await screen.findByText("Отдел с таким названием уже существует")).toBeInTheDocument();
  expect(submit).toHaveBeenCalledWith({ name: "ИТ", role: "admin" });

  await user.click(screen.getByRole("button", { name: "Сохранить" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Что-то не так");
});

function BlockersDemo() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>Деактивировать</button>
      <BlockersDialog
        open={open}
        message="Перед деактивацией нужно передать ответственность другим сотрудникам"
        blockers={[{ kind: "department_head", entity_id: 2, title: "Отдел «Бухгалтерия»" }]}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

// Диалоги в тестах открываются действием пользователя, как в приложении: MUI FocusTrap
// в jsdom падает при размонтировании диалога, открытого сразу при рендере.
test("BlockersDialog перечисляет причины блокировки", async () => {
  const { user } = renderWithProviders(<BlockersDemo />);

  await user.click(screen.getByRole("button", { name: "Деактивировать" }));

  expect(await screen.findByText("Отдел «Бухгалтерия»")).toBeInTheDocument();
  expect(screen.getByText("Руководитель отдела")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Понятно" }));
});
