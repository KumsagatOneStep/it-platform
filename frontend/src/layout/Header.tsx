import { AppBar, Box, IconButton, Toolbar } from "@mui/material";
import { IconMenu2 } from "@tabler/icons-react";

import { UserMenu } from "./UserMenu";

export function Header({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  return (
    <AppBar
      position="sticky"
      color="default"
      elevation={0}
      sx={{ bgcolor: "rgba(255,255,255,0.85)", backdropFilter: "blur(4px)" }}
    >
      <Toolbar sx={{ minHeight: 70 }}>
        <IconButton
          aria-label="Открыть меню"
          onClick={onOpenSidebar}
          sx={{ display: { lg: "none" } }}
        >
          <IconMenu2 size={22} stroke={1.5} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }} />
        <UserMenu />
      </Toolbar>
    </AppBar>
  );
}
