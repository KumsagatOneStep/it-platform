import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from "@mui/material";
import { useSnackbar } from "notistack";

interface TemporaryPasswordDialogProps {
  fullName: string;
  password: string;
  onClose: () => void;
}

export function TemporaryPasswordDialog({
  fullName,
  password,
  onClose,
}: TemporaryPasswordDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(password);
      enqueueSnackbar("Пароль скопирован", { variant: "success" });
    } catch {
      enqueueSnackbar("Не удалось скопировать, выделите пароль вручную", { variant: "warning" });
    }
  };
  return (
    <Dialog
      open
      onClose={(_, reason) => {
        if (reason !== "backdropClick" && reason !== "escapeKeyDown") onClose();
      }}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Временный пароль</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Alert severity="warning">
            Пароль показывается один раз. Передайте его пользователю «{fullName}» — при входе
            система попросит задать новый пароль.
          </Alert>
          <TextField
            label="Временный пароль"
            value={password}
            fullWidth
            slotProps={{ htmlInput: { readOnly: true } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={() => void copy()}>Скопировать</Button>
        <Button onClick={onClose} variant="contained">
          Готово
        </Button>
      </DialogActions>
    </Dialog>
  );
}
