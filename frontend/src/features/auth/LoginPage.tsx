import { Alert, Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { applyApiErrors } from "../../shared/lib/applyApiErrors";
import { useDocumentTitle } from "../../shared/lib/useDocumentTitle";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useAuth } from "./AuthContext";

interface LoginValues {
  email: string;
  password: string;
}

export function LoginPage() {
  useDocumentTitle("Вход");
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting },
  } = useForm<LoginValues>({ defaultValues: { email: "", password: "" } });

  // После успешного входа GuestOnly сам переведёт на ?next= или на главную.
  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      await login(email.trim(), password);
    } catch (error) {
      setFormError(applyApiErrors(error, setError, { fields: ["email", "password"] }));
    }
  });

  return (
    <Card sx={{ width: "100%", maxWidth: 450 }}>
      <CardContent sx={{ p: 4 }}>
        <Box sx={{ textAlign: "center", mb: 3 }}>
          <Typography variant="h3" component="h1">
            IT-платформа
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Вход в систему
          </Typography>
        </Box>
        <form onSubmit={onSubmit} noValidate>
          <Stack spacing={2.5}>
            {formError && <Alert severity="error">{formError}</Alert>}
            <FormTextField
              control={control}
              name="email"
              label="Email"
              type="email"
              autoComplete="username"
              autoFocus
              rules={{ required: "Введите email" }}
            />
            <FormTextField
              control={control}
              name="password"
              label="Пароль"
              type="password"
              autoComplete="current-password"
              rules={{ required: "Введите пароль" }}
            />
            <Button type="submit" variant="contained" size="large" loading={isSubmitting}>
              Войти
            </Button>
          </Stack>
        </form>
      </CardContent>
    </Card>
  );
}
