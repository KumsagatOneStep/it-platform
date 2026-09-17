import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
} from "@mui/material";

import type { Blocker } from "../../api/errors";

const KIND_LABELS: Record<string, string> = {
  department_head: "Руководитель отдела",
  ticket_type_default_assignee: "Исполнитель по умолчанию для типа заявки",
};

interface BlockersDialogProps {
  open: boolean;
  message: string;
  blockers: Blocker[];
  onClose: () => void;
}

export function BlockersDialog({ open, message, blockers, onClose }: BlockersDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Операция невозможна</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
        <List dense>
          {blockers.map((blocker) => (
            <ListItem key={`${blocker.kind}-${blocker.entity_id}`} disableGutters>
              <ListItemText
                primary={blocker.title}
                secondary={KIND_LABELS[blocker.kind] ?? blocker.kind}
              />
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="contained">
          Понятно
        </Button>
      </DialogActions>
    </Dialog>
  );
}
