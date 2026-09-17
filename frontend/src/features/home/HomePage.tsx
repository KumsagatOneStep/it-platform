import { Grid, Typography } from "@mui/material";

import { useAuth } from "../auth";
import { DashboardCard } from "../../shared/ui/DashboardCard";
import { PageContainer } from "../../shared/ui/PageContainer";

const PLACEHOLDERS = ["Мои заявки", "Заявки на мне", "Мои задачи", "Моя техника"];

export function HomePage() {
  const { user } = useAuth();
  return (
    <PageContainer title="Главная">
      <Typography variant="h5" sx={{ mb: 3 }}>
        Здравствуйте, {user?.full_name}
      </Typography>
      <Grid container spacing={3}>
        {PLACEHOLDERS.map((title) => (
          <Grid key={title} size={{ xs: 12, sm: 6, lg: 3 }}>
            <DashboardCard title={title}>
              <Typography color="text.secondary">Появится в следующих версиях</Typography>
            </DashboardCard>
          </Grid>
        ))}
      </Grid>
    </PageContainer>
  );
}
