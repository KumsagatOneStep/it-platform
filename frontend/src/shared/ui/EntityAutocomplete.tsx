import { Autocomplete, CircularProgress, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { useDebouncedValue } from "../lib/useDebouncedValue";

export interface EntityOption {
  id: number;
  label: string;
}

export interface EntityAutocompleteProps {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  /** Поиск вариантов на сервере; вызывается с пустой строкой при открытии. */
  fetchOptions: (query: string) => Promise<EntityOption[]>;
  /** Уникальный ключ источника вариантов для кэша TanStack Query. */
  queryKey: readonly unknown[];
  /** Подпись для текущего значения, если его нет среди загруженных вариантов. */
  labelFor: (id: number) => string;
  error?: boolean;
  helperText?: string;
  disabled?: boolean;
  onBlur?: () => void;
}

export function EntityAutocomplete({
  label,
  value,
  onChange,
  fetchOptions,
  queryKey,
  labelFor,
  error,
  helperText,
  disabled,
  onBlur,
}: EntityAutocompleteProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input);

  const options = useQuery({
    queryKey: [...queryKey, "options", query],
    queryFn: () => fetchOptions(query),
    enabled: open,
  });

  const selected: EntityOption | null =
    value === null ? null : { id: value, label: labelFor(value) };

  return (
    <Autocomplete<EntityOption>
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      value={selected}
      options={options.data ?? []}
      loading={options.isFetching}
      filterOptions={(items) => items}
      isOptionEqualToValue={(option, current) => option.id === current.id}
      getOptionLabel={(option) => option.label}
      onChange={(_, option) => onChange(option?.id ?? null)}
      onInputChange={(_, text, reason) => {
        if (reason === "input") setInput(text);
        if (reason === "clear" || reason === "reset") setInput("");
      }}
      disabled={disabled}
      noOptionsText={
        options.error
          ? options.error instanceof ApiError
            ? options.error.message
            : UNKNOWN_ERROR_MESSAGE
          : "Ничего не найдено"
      }
      loadingText="Загрузка…"
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          error={error}
          helperText={helperText}
          onBlur={onBlur}
          slotProps={{
            ...params.slotProps,
            input: {
              ...params.slotProps.input,
              endAdornment: (
                <>
                  {options.isFetching && <CircularProgress size={18} />}
                  {params.slotProps.input.endAdornment}
                </>
              ),
            },
          }}
        />
      )}
    />
  );
}
