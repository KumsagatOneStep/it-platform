import { InputAdornment, MenuItem, Stack, TextField } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { useEffect, useState, type ReactNode } from "react";

import { DEBOUNCE_MS } from "../lib/useDebouncedValue";

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

  useEffect(() => {
    setText(value);
  }, [value]);

  useEffect(() => {
    if (text === value) return;
    const timer = setTimeout(() => onChange(text), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text, value, onChange]);

  return (
    <TextField
      size="small"
      value={text}
      onChange={(event) => setText(event.target.value)}
      placeholder={placeholder}
      sx={{ minWidth: 260 }}
      slotProps={{
        htmlInput: { "aria-label": placeholder },
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
