import { Button, Chip, Stack } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useSnackbar } from "notistack";
import { useState } from "react";

import { ApiError, blockersOf, type Blocker } from "../../api/errors";
import type { Schemas } from "../../api/types";
import { formatDate, ROLE_LABELS } from "../../shared/lib/format";
import {
  booleanParam,
  enumParam,
  idParam,
  textParam,
  useUrlFilters,
} from "../../shared/lib/useUrlFilters";
import { useDepartments } from "../../shared/lookups/departments";
import { BlockersDialog } from "../../shared/ui/BlockersDialog";
import { ConfirmDialog } from "../../shared/ui/ConfirmDialog";
import { DataTable, type Column, type RowAction } from "../../shared/ui/DataTable";
import { FilterBar, FilterSelect, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAdminUsers, useIssueTemporaryPassword, useSetUserActive, useUnlockLogin } from "./api";
import { TemporaryPasswordDialog } from "./TemporaryPasswordDialog";
import { ROLE_OPTIONS, UserFormDialog } from "./UserFormDialog";

type User = Schemas["UserRead"];
type Confirmation = { kind: "deactivate" | "activate" | "password" | "unlock"; user: User };

const FILTERS = {
  q: textParam,
  role: enumParam(["employee", "manager", "admin"] as const),
  department: idParam,
  active: booleanParam,
};

const STATUS_OPTIONS = [
  { value: "true", label: "Активные" },
  { value: "false", label: "Деактивированные" },
] as const;

const CONFIRM_TEXT: Record<Confirmation["kind"], { title: string; text: string; label: string }> = {
  deactivate: {
    title: "Деактивировать пользователя?",
    text: "Пользователь не сможет войти, его сессии будут завершены.",
    label: "Деактивировать",
  },
  activate: {
    title: "Активировать пользователя?",
    text: "Пользователь снова сможет войти в систему.",
    label: "Активировать",
  },
  password: {
    title: "Выдать временный пароль?",
    text: "Текущий пароль перестанет действовать, сессии пользователя будут завершены.",
    label: "Выдать пароль",
  },
  unlock: {
    title: "Снять блокировку входа?",
    text: "Счётчики неудачных попыток входа для этого пользователя будут сброшены.",
    label: "Снять блокировку",
  },
};

export function UsersPage() {
  const { enqueueSnackbar } = useSnackbar();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const users = useAdminUsers({
    q: filters.q,
    role: filters.role,
    departmentId: filters.department,
    isActive: filters.active,
    limit,
    offset,
  });
  const departments = useDepartments();
  const setActive = useSetUserActive();
  const issuePassword = useIssueTemporaryPassword();
  const unlockLogin = useUnlockLogin();

  const [editing, setEditing] = useState<User | "new" | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [password, setPassword] = useState<{ fullName: string; value: string } | null>(null);
  const [blocked, setBlocked] = useState<{ message: string; blockers: Blocker[] } | null>(null);

  const departmentName = (id: number | null) =>
    id === null ? "—" : (departments.data?.find((item) => item.id === id)?.name ?? "…");

  /** Показывает диалог причин, если операция заблокирована; возвращает true, если показал. */
  const showBlockers = (error: unknown) => {
    if (
      error instanceof ApiError &&
      (error.code === "deactivation_blocked" || error.code === "role_change_blocked")
    ) {
      setBlocked({ message: error.message, blockers: blockersOf(error) });
      return true;
    }
    return false;
  };

  const confirm = async () => {
    if (!confirmation) return;
    const { kind, user } = confirmation;
    try {
      if (kind === "deactivate" || kind === "activate") {
        await setActive.mutateAsync({ id: user.id, active: kind === "activate" });
        enqueueSnackbar(
          kind === "activate" ? "Пользователь активирован" : "Пользователь деактивирован",
          {
            variant: "success",
          },
        );
      } else if (kind === "password") {
        const result = await issuePassword.mutateAsync(user.id);
        setPassword({ fullName: user.full_name, value: result.temporary_password });
      } else {
        await unlockLogin.mutateAsync(user.id);
        enqueueSnackbar("Блокировка входа снята", { variant: "success" });
      }
    } catch (error) {
      if (!showBlockers(error)) {
        enqueueSnackbar(error instanceof ApiError ? error.message : "Не удалось выполнить запрос", {
          variant: "error",
        });
      }
    } finally {
      setConfirmation(null);
    }
  };

  const columns: Column<User>[] = [
    { key: "full_name", header: "ФИО", render: (user) => user.full_name },
    { key: "email", header: "Email", render: (user) => user.email },
    { key: "role", header: "Роль", render: (user) => ROLE_LABELS[user.role] },
    { key: "department", header: "Отдел", render: (user) => departmentName(user.department_id) },
    {
      key: "status",
      header: "Статус",
      render: (user) => (
        <Stack direction="row" spacing={1}>
          <Chip
            size="small"
            label={user.is_active ? "Активен" : "Деактивирован"}
            color={user.is_active ? "success" : "default"}
          />
          {user.must_change_password && (
            <Chip size="small" label="Временный пароль" color="warning" />
          )}
        </Stack>
      ),
    },
    { key: "created_at", header: "Создан", render: (user) => formatDate(user.created_at) },
  ];

  const rowActions: RowAction<User>[] = [
    { label: "Редактировать", onClick: (user) => setEditing(user) },
    {
      label: "Выдать временный пароль",
      onClick: (user) => setConfirmation({ kind: "password", user }),
    },
    {
      label: "Снять блокировку входа",
      onClick: (user) => setConfirmation({ kind: "unlock", user }),
    },
    {
      label: "Деактивировать",
      color: "error",
      hidden: (user) => !user.is_active,
      onClick: (user) => setConfirmation({ kind: "deactivate", user }),
    },
    {
      label: "Активировать",
      hidden: (user) => user.is_active,
      onClick: (user) => setConfirmation({ kind: "activate", user }),
    },
  ];

  const pending = setActive.isPending || issuePassword.isPending || unlockLogin.isPending;
  const confirmText = confirmation ? CONFIRM_TEXT[confirmation.kind] : null;

  return (
    <PageContainer
      title="Пользователи"
      breadcrumbs={[{ label: "Администрирование" }, { label: "Пользователи" }]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setEditing("new")}
        >
          Добавить
        </Button>
      }
    >
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Поиск по ФИО и email"
        />
        <FilterSelect
          label="Роль"
          value={filters.role}
          options={ROLE_OPTIONS}
          onChange={(value) => setFilter("role", value)}
        />
        <FilterSelect
          label="Отдел"
          value={filters.department}
          options={(departments.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("department", value)}
        />
        <FilterSelect
          label="Статус"
          value={filters.active === null ? null : filters.active ? "true" : "false"}
          options={STATUS_OPTIONS}
          onChange={(value) => setFilter("active", value === null ? null : value === "true")}
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={users.data?.items}
        getRowId={(user) => user.id}
        loading={users.isLoading}
        error={users.error}
        onRetry={() => void users.refetch()}
        emptyText="Пользователи не найдены"
        rowActions={rowActions}
        paging={{ limit, offset, total: users.data?.total ?? 0, onChange: setPage }}
      />

      {editing && (
        <UserFormDialog
          user={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onCreated={(result) => {
            setEditing(null);
            setPassword({ fullName: result.user.full_name, value: result.temporary_password });
          }}
          onBlocked={(error) => {
            if (!showBlockers(error)) return false;
            setEditing(null);
            return true;
          }}
        />
      )}
      {confirmation && confirmText && (
        <ConfirmDialog
          open
          title={confirmText.title}
          text={confirmText.text}
          confirmLabel={confirmText.label}
          confirmColor={confirmation.kind === "deactivate" ? "error" : "primary"}
          pending={pending}
          onConfirm={() => void confirm()}
          onClose={() => setConfirmation(null)}
        />
      )}
      {password && (
        <TemporaryPasswordDialog
          fullName={password.fullName}
          password={password.value}
          onClose={() => setPassword(null)}
        />
      )}
      {blocked && (
        <BlockersDialog
          open
          message={blocked.message}
          blockers={blocked.blockers}
          onClose={() => setBlocked(null)}
        />
      )}
    </PageContainer>
  );
}
