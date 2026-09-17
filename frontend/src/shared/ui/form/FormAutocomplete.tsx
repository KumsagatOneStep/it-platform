import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

import { EntityAutocomplete, type EntityAutocompleteProps } from "../EntityAutocomplete";

type FormAutocompleteProps<T extends FieldValues> = {
  control: Control<T>;
  name: FieldPath<T>;
} & Omit<EntityAutocompleteProps, "value" | "onChange" | "error" | "helperText" | "onBlur">;

export function FormAutocomplete<T extends FieldValues>({
  control,
  name,
  ...props
}: FormAutocompleteProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <EntityAutocomplete
          {...props}
          value={(field.value as number | null | undefined) ?? null}
          onChange={field.onChange}
          onBlur={field.onBlur}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message}
        />
      )}
    />
  );
}
