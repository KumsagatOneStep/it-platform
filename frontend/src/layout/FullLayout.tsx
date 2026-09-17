import { Box, Container } from "@mui/material";
import { useState, type ReactNode } from "react";
import { Outlet } from "react-router";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function FullLayout({ children }: { children?: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <Box sx={{ display: "flex", flexDirection: "column", flexGrow: 1, minWidth: 0 }}>
        <Header onOpenSidebar={() => setMobileOpen(true)} />
        <Container component="main" maxWidth="lg" sx={{ py: 3 }}>
          {children ?? <Outlet />}
        </Container>
      </Box>
    </Box>
  );
}
