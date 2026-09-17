import { MenuItem, TextField } from "@mui/material";
import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

export interface SelectOption<V extends string | number> {
  value: V;
  label: string;
}

interface FormSelectProps<T extends FieldValues, V extends string | number> {
  control: Control<T>;
  name: FieldPath<T>;
  label: string;
  options: readonly SelectOption<V>[];
  /** Подпись пустого значения; если задана, поле допускает null. */
  emptyLabel?: string;
  disabled?: boolean;
}

export function FormSelect<T extends FieldValues, V extends string | number>({
  control,
  name,
  label,
  options,
  emptyLabel,
  disabled,
}: FormSelectProps<T, V>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <TextField
          select
          fullWidth
          label={label}
          name={field.name}
          inputRef={field.ref}
          value={field.value === null || field.value === undefined ? "" : String(field.value)}
          onChange={(event) => {
            const option = options.find((item) => String(item.value) === event.target.value);
            field.onChange(option ? option.value : null);
          }}
          onBlur={field.onBlur}
          disabled={disabled}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message}
        >
          {emptyLabel !== undefined && <MenuItem value="">{emptyLabel}</MenuItem>}
          {options.map((option) => (
            <MenuItem key={String(option.value)} value={String(option.value)}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  );
}
