import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  ListItemIcon,
  Menu,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from "@mui/material";
import { IconDotsVertical } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { PAGE_SIZES } from "../lib/useUrlFilters";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: number | string;
  align?: "left" | "right" | "center";
}

export interface RowAction<T> {
  label: string;
  icon?: ReactNode;
  onClick: (row: T) => void;
  hidden?: (row: T) => boolean;
  color?: "error";
}

export interface TablePaging {
  limit: number;
  offset: number;
  onChange: (offset: number, limit: number) => void;
  /** Общее число строк на сервере; если не задано — пагинация по `rows` на клиенте. */
  total?: number;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  getRowId: (row: T) => string | number;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  emptyText?: string;
  rowActions?: RowAction<T>[];
  paging?: TablePaging;
}

function RowActionsMenu<T>({ row, actions }: { row: T; actions: RowAction<T>[] }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const visible = actions.filter((action) => !action.hidden?.(row));
  if (visible.length === 0) return null;
  return (
    <>
      <IconButton aria-label="Действия" onClick={(event) => setAnchor(event.currentTarget)}>
        <IconDotsVertical size={18} stroke={1.5} />
      </IconButton>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {visible.map((action) => (
          <MenuItem
            key={action.label}
            onClick={() => {
              setAnchor(null);
              action.onClick(row);
            }}
            sx={action.color === "error" ? { color: "error.main" } : undefined}
          >
            {action.icon && <ListItemIcon sx={{ color: "inherit" }}>{action.icon}</ListItemIcon>}
            {action.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  loading = false,
  error,
  onRetry,
  emptyText = "Нет данных",
  rowActions,
  paging,
}: DataTableProps<T>) {
  const clientPaging = paging !== undefined && paging.total === undefined;
  const visibleRows =
    rows && clientPaging ? rows.slice(paging.offset, paging.offset + paging.limit) : rows;
  const columnCount = columns.length + (rowActions ? 1 : 0);

  let body: ReactNode;
  if (error) {
    body = (
      <TableRow>
        <TableCell colSpan={columnCount}>
          <Alert
            severity="error"
            action={
              onRetry && (
                <Button color="inherit" size="small" onClick={onRetry}>
                  Повторить
                </Button>
              )
            }
          >
            {error instanceof ApiError ? error.message : UNKNOWN_ERROR_MESSAGE}
          </Alert>
        </TableCell>
      </TableRow>
    );
  } else if (loading && !rows) {
    body = (
      <TableRow>
        <TableCell colSpan={columnCount} align="center" sx={{ py: 6 }}>
          <CircularProgress size={28} aria-label="Загрузка" />
        </TableCell>
      </TableRow>
    );
  } else if (!visibleRows || visibleRows.length === 0) {
    body = (
      <TableRow>
        <TableCell colSpan={columnCount} align="center" sx={{ py: 6 }}>
          <Typography color="text.secondary">{emptyText}</Typography>
        </TableCell>
      </TableRow>
    );
  } else {
    body = visibleRows.map((row) => (
      <TableRow key={getRowId(row)} hover>
        {columns.map((column) => (
          <TableCell key={column.key} align={column.align}>
            {column.render(row)}
          </TableCell>
        ))}
        {rowActions && (
          <TableCell align="right" sx={{ width: 56 }}>
            <RowActionsMenu row={row} actions={rowActions} />
          </TableCell>
        )}
      </TableRow>
    ));
  }

  return (
    <Paper variant="outlined">
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  align={column.align}
                  sx={{ width: column.width, fontWeight: 600, whiteSpace: "nowrap" }}
                >
                  {column.header}
                </TableCell>
              ))}
              {rowActions && (
                <TableCell>
                  <Box component="span" sx={visuallyHidden}>
                    Действия
                  </Box>
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>{body}</TableBody>
        </Table>
      </TableContainer>
      {paging && (
        <TablePagination
          component="div"
          count={paging.total ?? rows?.length ?? 0}
          page={Math.floor(paging.offset / paging.limit)}
          rowsPerPage={paging.limit}
          rowsPerPageOptions={[...PAGE_SIZES]}
          onPageChange={(_, page) => paging.onChange(page * paging.limit, paging.limit)}
          onRowsPerPageChange={(event) => paging.onChange(0, Number(event.target.value))}
        />
      )}
    </Paper>
  );
}

const visuallyHidden = {
  position: "absolute",
  width: 1,
  height: 1,
  overflow: "hidden",
  clip: "rect(0 0 0 0)",
  whiteSpace: "nowrap",
} as const;
