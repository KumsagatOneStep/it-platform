import { screen, waitFor } from "@testing-library/react";
import { useState } from "react";

import { ApiError } from "../../api/errors";
import { renderWithProviders } from "../../test/render";
import { EntityAutocomplete, type EntityOption } from "./EntityAutocomplete";

const PEOPLE: EntityOption[] = [
  { id: 1, label: "Иванов Иван" },
  { id: 2, label: "Петров Пётр" },
];

function Demo({ fetchOptions }: { fetchOptions: (q: string) => Promise<EntityOption[]> }) {
  const [value, setValue] = useState<number | null>(2);
  return (
    <>
      <EntityAutocomplete
        label="Руководитель"
        value={value}
        onChange={setValue}
        fetchOptions={fetchOptions}
        queryKey={["people"]}
        labelFor={(id) => PEOPLE.find((person) => person.id === id)?.label ?? `#${id}`}
      />
      <output>{String(value)}</output>
    </>
  );
}

test("ищет на сервере, выбирает и очищает значение", async () => {
  const fetchOptions = vi.fn(async (query: string) =>
    PEOPLE.filter((person) => person.label.toLowerCase().includes(query.toLowerCase())),
  );
  const { user } = renderWithProviders(<Demo fetchOptions={fetchOptions} />);
  const input = screen.getByLabelText("Руководитель");
  expect(input).toHaveValue("Петров Пётр");

  await user.clear(input);
  await user.type(input, "иван");
  await waitFor(() => expect(fetchOptions).toHaveBeenLastCalledWith("иван"));
  await user.click(await screen.findByRole("option", { name: "Иванов Иван" }));
  expect(screen.getByRole("status")).toHaveTextContent("1");

  await user.click(screen.getByRole("button", { name: "Очистить" }));
  expect(screen.getByRole("status")).toHaveTextContent("null");
});

test("ошибка загрузки вариантов показывается вместо «Ничего не найдено»", async () => {
  const fetchOptions = vi.fn(async () => {
    throw new ApiError({ status: 0, code: "network_error", message: "Нет связи с сервером" });
  });
  const { user } = renderWithProviders(<Demo fetchOptions={fetchOptions} />);

  await user.click(screen.getByLabelText("Руководитель"));

  expect(await screen.findByText("Нет связи с сервером")).toBeInTheDocument();
});
