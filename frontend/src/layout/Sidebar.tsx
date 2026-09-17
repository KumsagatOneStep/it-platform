import { Box, Drawer, useMediaQuery, type Theme } from "@mui/material";

import { Logo } from "./Logo";
import { SidebarMenu } from "./SidebarMenu";

export const SIDEBAR_WIDTH = 270;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ mobileOpen, onMobileClose }: SidebarProps) {
  const lgUp = useMediaQuery((theme: Theme) => theme.breakpoints.up("lg"));
  const content = (
    <>
      <Logo />
      <SidebarMenu onNavigate={lgUp ? undefined : onMobileClose} />
    </>
  );

  if (lgUp) {
    return (
      <Box sx={{ width: SIDEBAR_WIDTH, flexShrink: 0 }}>
        <Drawer
          variant="permanent"
          anchor="left"
          slotProps={{ paper: { sx: { width: SIDEBAR_WIDTH, boxSizing: "border-box" } } }}
        >
          {content}
        </Drawer>
      </Box>
    );
  }
  return (
    <Drawer
      variant="temporary"
      anchor="left"
      open={mobileOpen}
      onClose={onMobileClose}
      slotProps={{
        paper: { sx: { width: SIDEBAR_WIDTH, boxShadow: (theme) => theme.shadows[8] } },
      }}
    >
      {content}
    </Drawer>
  );
}
