import { Button, Stack, Typography } from "@mui/material";
import { Link } from "react-router";

import { ROLE_LABELS } from "../../shared/lib/format";
import { useDepartments } from "../../shared/lookups/departments";
import { DashboardCard } from "../../shared/ui/DashboardCard";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAuth } from "./AuthContext";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography>{value}</Typography>
    </div>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  const departments = useDepartments();
  if (!user) return null;

  const department =
    user.department_id === null
      ? "Без отдела"
      : (departments.data?.find((item) => item.id === user.department_id)?.name ?? "…");

  return (
    <PageContainer title="Профиль">
      <DashboardCard>
        <Stack spacing={2}>
          <Field label="ФИО" value={user.full_name} />
          <Field label="Email" value={user.email} />
          <Field label="Роль" value={ROLE_LABELS[user.role]} />
          <Field label="Отдел" value={department} />
          <div>
            <Button component={Link} to="/change-password" variant="outlined">
              Сменить пароль
            </Button>
          </div>
        </Stack>
      </DashboardCard>
    </PageContainer>
  );
}
