import { screen, within } from "@testing-library/react";

import { ApiError } from "../../api/errors";
import { renderWithProviders } from "../../test/render";
import { DataTable, type Column } from "./DataTable";

interface Row {
  id: number;
  name: string;
}

const columns: Column<Row>[] = [{ key: "name", header: "Название", render: (row) => row.name }];
const rows: Row[] = Array.from({ length: 30 }, (_, index) => ({
  id: index + 1,
  name: `Отдел ${index + 1}`,
}));

test("показывает строки, действия и клиентскую пагинацию", async () => {
  const onChange = vi.fn();
  const onEdit = vi.fn();
  const { user } = renderWithProviders(
    <DataTable
      columns={columns}
      rows={rows}
      getRowId={(row) => row.id}
      rowActions={[{ label: "Редактировать", onClick: onEdit }]}
      paging={{ limit: 25, offset: 25, onChange }}
    />,
  );

  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("row")).toHaveLength(6); // заголовок + 5 строк второй страницы
  expect(screen.getByText("26–30 из 30")).toBeInTheDocument();

  await user.click(within(table).getAllByRole("button", { name: "Действия" })[0]!);
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  expect(onEdit).toHaveBeenCalledWith({ id: 26, name: "Отдел 26" });

  await user.click(screen.getByRole("button", { name: "Перейти на предыдущую страницу" }));
  expect(onChange).toHaveBeenCalledWith(0, 25);
});

test("серверная пагинация берёт total из ответа", () => {
  renderWithProviders(
    <DataTable
      columns={columns}
      rows={rows.slice(0, 25)}
      getRowId={(row) => row.id}
      paging={{ limit: 25, offset: 0, total: 120, onChange: vi.fn() }}
    />,
  );

  expect(screen.getAllByRole("row")).toHaveLength(26);
  expect(screen.getByText("1–25 из 120")).toBeInTheDocument();
});

test("пустой список и ошибка с повтором", async () => {
  const onRetry = vi.fn();
  const { user, rerender } = renderWithProviders(
    <DataTable columns={columns} rows={[]} getRowId={(row) => row.id} emptyText="Отделов нет" />,
  );
  expect(screen.getByText("Отделов нет")).toBeInTheDocument();

  rerender(
    <DataTable
      columns={columns}
      rows={undefined}
      getRowId={(row) => row.id}
      error={new ApiError({ status: 500, code: "internal_error", message: "Внутренняя ошибка" })}
      onRetry={onRetry}
    />,
  );
  await user.click(screen.getByRole("button", { name: "Повторить" }));
  expect(screen.getByText("Внутренняя ошибка")).toBeInTheDocument();
  expect(onRetry).toHaveBeenCalled();
});
