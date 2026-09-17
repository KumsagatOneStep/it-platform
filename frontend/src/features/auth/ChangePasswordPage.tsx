import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router";

import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useDocumentTitle } from "../../shared/lib/useDocumentTitle";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useAuth } from "./AuthContext";
import { safeNext } from "./next";

interface ChangePasswordValues {
  current_password: string;
  new_password: string;
  repeat_password: string;
}

const fieldForError = fieldByCode<ChangePasswordValues>({
  invalid_current_password: "current_password",
  password_reused: "new_password",
  weak_password: "new_password",
});

export function ChangePasswordPage({ forced = false }: { forced?: boolean }) {
  useDocumentTitle("Смена пароля");
  const { changePassword, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    getValues,
    formState: { isSubmitting },
  } = useForm<ChangePasswordValues>({
    defaultValues: { current_password: "", new_password: "", repeat_password: "" },
  });

  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    setFormError(null);
    try {
      await changePassword(current_password, new_password);
      enqueueSnackbar("Пароль изменён", { variant: "success" });
      void navigate(safeNext(searchParams.get("next")), { replace: true });
    } catch (error) {
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["current_password", "new_password"],
          fieldForError,
        }),
      );
    }
  });

  return (
    <Card sx={{ width: "100%", maxWidth: 480 }}>
      <CardContent sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
          Смена пароля
        </Typography>
        <form onSubmit={onSubmit} noValidate>
          <Stack spacing={2.5}>
            {forced && (
              <Alert severity="info">
                Администратор выдал вам временный пароль. Задайте новый пароль, чтобы продолжить.
              </Alert>
            )}
            {formError && <Alert severity="error">{formError}</Alert>}
            <FormTextField
              control={control}
              name="current_password"
              label="Текущий пароль"
              type="password"
              autoComplete="current-password"
              rules={{ required: "Введите текущий пароль" }}
            />
            <FormTextField
              control={control}
              name="new_password"
              label="Новый пароль"
              type="password"
              autoComplete="new-password"
              rules={{ required: "Введите новый пароль" }}
            />
            <FormTextField
              control={control}
              name="repeat_password"
              label="Повторите новый пароль"
              type="password"
              autoComplete="new-password"
              rules={{
                required: "Повторите новый пароль",
                validate: (value) => value === getValues("new_password") || "Пароли не совпадают",
              }}
            />
            <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
              {forced && (
                <Button color="inherit" onClick={() => void logout()}>
                  Выйти
                </Button>
              )}
              <Button type="submit" variant="contained" loading={isSubmitting}>
                Сменить пароль
              </Button>
            </Stack>
          </Stack>
        </form>
      </CardContent>
    </Card>
  );
}
