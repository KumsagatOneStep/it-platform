import { Card, CardContent, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

interface DashboardCardProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children?: ReactNode;
}

export function DashboardCard({ title, subtitle, action, children }: DashboardCardProps) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent sx={{ p: "30px" }}>
        {(title || action) && (
          <Stack direction="row" spacing={2} sx={{ mb: 3, justifyContent: "space-between" }}>
            <div>
              {title && <Typography variant="h5">{title}</Typography>}
              {subtitle && (
                <Typography variant="subtitle2" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </div>
            {action}
          </Stack>
        )}
        {children}
      </CardContent>
    </Card>
  );
}
