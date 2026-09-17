import { Box, Typography } from "@mui/material";
import { IconDeviceDesktopCog } from "@tabler/icons-react";
import { Link } from "react-router";

export function Logo() {
  return (
    <Box
      component={Link}
      to="/"
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        height: 70,
        px: 3,
        color: "text.primary",
      }}
    >
      <Box sx={{ color: "primary.main", display: "flex" }}>
        <IconDeviceDesktopCog size={28} stroke={1.5} />
      </Box>
      <Typography variant="h5" component="span">
        IT-платформа
      </Typography>
    </Box>
  );
}
