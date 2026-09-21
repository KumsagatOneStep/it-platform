import { screen, waitFor } from "@testing-library/react";
import { useState } from "react";

import { DEBOUNCE_MS } from "../lib/useDebouncedValue";
import { renderWithProviders } from "../../test/render";
import { SearchField } from "./FilterBar";

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

test("одни пробелы не меняют поиск", async () => {
  const onChange = vi.fn();
  const { user } = renderWithProviders(<SearchField value="" onChange={onChange} />);

  await user.type(screen.getByLabelText("Поиск"), "  ");
  await pause(DEBOUNCE_MS * 2);

  expect(onChange).not.toHaveBeenCalled();
});

test("сообщает введённый текст один раз после паузы", async () => {
  const onChange = vi.fn();
  const { user } = renderWithProviders(<SearchField value="" onChange={onChange} />);

  await user.type(screen.getByLabelText("Поиск"), "ив");

  await waitFor(() => expect(onChange).toHaveBeenCalledWith("ив"));
  await pause(DEBOUNCE_MS * 2);
  expect(onChange).toHaveBeenCalledTimes(1);
});

test("длина запроса ограничена 100 символами", () => {
  renderWithProviders(<SearchField value="" onChange={vi.fn()} />);

  expect(screen.getByLabelText("Поиск")).toHaveAttribute("maxLength", "100");
});

test("внешний сброс значения не возвращает старый текст", async () => {
  const onChange = vi.fn();
  function Harness() {
    const [value, setValue] = useState("");
    return (
      <>
        <SearchField
          value={value}
          onChange={(next) => {
            onChange(next);
            setValue(next);
          }}
        />
        <button onClick={() => setValue("")}>Сбросить</button>
      </>
    );
  }
  const { user } = renderWithProviders(<Harness />);

  await user.type(screen.getByLabelText("Поиск"), "ив");
  await waitFor(() => expect(onChange).toHaveBeenCalledWith("ив"));
  await user.click(screen.getByRole("button", { name: "Сбросить" }));
  await pause(DEBOUNCE_MS * 2);

  expect(screen.getByLabelText("Поиск")).toHaveValue("");
  expect(onChange).toHaveBeenCalledTimes(1);
});
