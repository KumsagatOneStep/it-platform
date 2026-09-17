import { Box } from "@mui/material";
import type { ReactNode } from "react";
import { Outlet } from "react-router";

export function BlankLayout({ children }: { children?: ReactNode }) {
  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        p: 2,
        background: "radial-gradient(#d2f1df, #d3d7fa, #bad8f4) 0% 0% / 400% 400%",
      }}
    >
      {children ?? <Outlet />}
    </Box>
  );
}
