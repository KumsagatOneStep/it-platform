import { InputAdornment, MenuItem, Stack, TextField } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { useDebouncedValue } from "../lib/useDebouncedValue";

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={2}
      sx={{ mb: 2, alignItems: { md: "center" } }}
    >
      {children}
    </Stack>
  );
}

interface SearchFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

/** Поле поиска: сообщает значение не чаще раза в 300 мс. */
export function SearchField({ value, onChange, placeholder = "Поиск" }: SearchFieldProps) {
  const [text, setText] = useState(value);
  const debounced = useDebouncedValue(text);
  const latest = useRef({ value, onChange });

  useEffect(() => {
    latest.current = { value, onChange };
    setText((current) => (current.trim() === value.trim() ? current : value));
  }, [value, onChange]);

  // Срабатывает только на новый debounced-текст: внешний сброс value не возвращает старый ввод.
  useEffect(() => {
    if (debounced.trim() !== latest.current.value.trim()) latest.current.onChange(debounced);
  }, [debounced]);

  return (
    <TextField
      size="small"
      value={text}
      onChange={(event) => setText(event.target.value)}
      placeholder={placeholder}
      sx={{ minWidth: 260 }}
      slotProps={{
        htmlInput: { "aria-label": placeholder, maxLength: 100 },
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <IconSearch size={18} stroke={1.5} />
            </InputAdornment>
          ),
        },
      }}
    />
  );
}

interface FilterSelectProps<V extends string | number> {
  label: string;
  value: V | null;
  options: readonly { value: V; label: string }[];
  onChange: (value: V | null) => void;
  allLabel?: string;
}

export function FilterSelect<V extends string | number>({
  label,
  value,
  options,
  onChange,
  allLabel = "Все",
}: FilterSelectProps<V>) {
  return (
    <TextField
      select
      size="small"
      label={label}
      value={value === null ? "" : String(value)}
      onChange={(event) =>
        onChange(
          options.find((option) => String(option.value) === event.target.value)?.value ?? null,
        )
      }
      sx={{ minWidth: 200 }}
    >
      <MenuItem value="">{allLabel}</MenuItem>
      {options.map((option) => (
        <MenuItem key={String(option.value)} value={String(option.value)}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}
