import { Box, CircularProgress } from "@mui/material";

export function FullScreenLoader() {
  return (
    <Box
      role="progressbar"
      aria-label="Загрузка"
      sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}
    >
      <CircularProgress />
    </Box>
  );
}
