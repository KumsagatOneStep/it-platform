import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
} from "@mui/material";
import type { FormEventHandler, ReactNode } from "react";

interface FormDialogProps {
  open: boolean;
  title: string;
  submitting: boolean;
  formError: string | null;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onClose: () => void;
  submitLabel?: string;
  children: ReactNode;
}

export function FormDialog({
  open,
  title,
  submitting,
  formError,
  onSubmit,
  onClose,
  submitLabel = "Сохранить",
  children,
}: FormDialogProps) {
  const close = () => {
    if (!submitting) onClose();
  };
  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="sm">
      <form onSubmit={onSubmit} noValidate aria-label={title}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ pt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}
            {children}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={close} disabled={submitting} color="inherit">
            Отмена
          </Button>
          <Button type="submit" variant="contained" loading={submitting}>
            {submitLabel}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
