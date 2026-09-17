import {
  Avatar,
  Box,
  Button,
  Divider,
  ListItemIcon,
  Menu,
  MenuItem,
  Typography,
} from "@mui/material";
import { IconKey, IconLogout, IconUserCircle } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../features/auth";
import { initialsOf, ROLE_LABELS } from "../shared/lib/format";

export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  if (!user) return null;

  const go = (path: string) => {
    setAnchor(null);
    void navigate(path);
  };
  const signOut = async () => {
    setAnchor(null);
    await logout();
    void navigate("/login", { replace: true });
  };

  return (
    <>
      <Button
        color="inherit"
        onClick={(event) => setAnchor(event.currentTarget)}
        aria-label="Меню пользователя"
        sx={{ gap: 1.5, textAlign: "left" }}
      >
        <Avatar sx={{ width: 35, height: 35, bgcolor: "primary.main", fontSize: "0.875rem" }}>
          {initialsOf(user.full_name)}
        </Avatar>
        <Box sx={{ display: { xs: "none", sm: "block" } }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            {user.full_name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {ROLE_LABELS[user.role]}
          </Typography>
        </Box>
      </Button>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
      >
        <MenuItem onClick={() => go("/profile")}>
          <ListItemIcon>
            <IconUserCircle size={20} stroke={1.5} />
          </ListItemIcon>
          Профиль
        </MenuItem>
        <MenuItem onClick={() => go("/change-password")}>
          <ListItemIcon>
            <IconKey size={20} stroke={1.5} />
          </ListItemIcon>
          Сменить пароль
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => void signOut()}>
          <ListItemIcon>
            <IconLogout size={20} stroke={1.5} />
          </ListItemIcon>
          Выйти
        </MenuItem>
      </Menu>
    </>
  );
}
