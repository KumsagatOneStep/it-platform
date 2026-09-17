import { Box, Breadcrumbs, Link as MuiLink, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { useDocumentTitle } from "../lib/useDocumentTitle";

export interface Breadcrumb {
  label: string;
  to?: string;
}

interface PageContainerProps {
  title: string;
  breadcrumbs?: Breadcrumb[];
  actions?: ReactNode;
  children: ReactNode;
}

export function PageContainer({ title, breadcrumbs = [], actions, children }: PageContainerProps) {
  useDocumentTitle(title);
  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ mb: 3, justifyContent: "space-between", alignItems: { sm: "center" } }}
      >
        <Box>
          <Typography variant="h3" component="h1">
            {title}
          </Typography>
          {breadcrumbs.length > 0 && (
            <Breadcrumbs sx={{ mt: 0.5 }}>
              {breadcrumbs.map((crumb) =>
                crumb.to ? (
                  <MuiLink key={crumb.label} component={Link} to={crumb.to} color="inherit">
                    {crumb.label}
                  </MuiLink>
                ) : (
                  <Typography key={crumb.label} color="text.secondary">
                    {crumb.label}
                  </Typography>
                ),
              )}
            </Breadcrumbs>
          )}
        </Box>
        {actions && (
          <Stack direction="row" spacing={1}>
            {actions}
          </Stack>
        )}
      </Stack>
      {children}
    </Box>
  );
}
