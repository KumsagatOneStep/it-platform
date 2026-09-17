import { Box, Button, Typography } from "@mui/material";
import { Link } from "react-router";

import { useDocumentTitle } from "../lib/useDocumentTitle";

interface StatusPageProps {
  code: number;
  title: string;
  text: string;
}

export function StatusPage({ code, title, text }: StatusPageProps) {
  useDocumentTitle(title);
  return (
    <Box sx={{ minHeight: "60vh", display: "grid", placeItems: "center", textAlign: "center" }}>
      <Box>
        <Typography variant="h1" color="primary" sx={{ fontSize: "4rem", lineHeight: 1 }}>
          {code}
        </Typography>
        <Typography variant="h4" component="h1" sx={{ mt: 2 }}>
          {title}
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          {text}
        </Typography>
        <Button component={Link} to="/" variant="contained">
          На главную
        </Button>
      </Box>
    </Box>
  );
}
