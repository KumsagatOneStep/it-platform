import { List, ListItemButton, ListItemIcon, ListItemText, ListSubheader } from "@mui/material";
import { NavLink } from "react-router";

import { useAuth } from "../features/auth";
import { menuForRole } from "./menu";

export function SidebarMenu({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <nav aria-label="Основное меню">
      {menuForRole(user.role).map((section) => (
        <List
          key={section.title ?? "main"}
          sx={{ px: 3 }}
          subheader={
            section.title ? (
              <ListSubheader
                disableSticky
                sx={{ px: 0, fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase" }}
              >
                {section.title}
              </ListSubheader>
            ) : undefined
          }
        >
          {section.items.map(({ label, to, icon: Icon }) => (
            <ListItemButton
              key={to}
              component={NavLink}
              to={to}
              end={to === "/"}
              onClick={onNavigate}
              sx={{
                borderRadius: "7px",
                mb: 0.5,
                color: "text.secondary",
                "&.active": {
                  bgcolor: "primary.main",
                  color: "primary.contrastText",
                  "&:hover": { bgcolor: "primary.dark" },
                  "& .MuiListItemIcon-root": { color: "inherit" },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: "inherit" }}>
                <Icon size="1.3rem" stroke={1.5} />
              </ListItemIcon>
              <ListItemText primary={label} />
            </ListItemButton>
          ))}
        </List>
      ))}
    </nav>
  );
}
