import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
  type RegisterOptions,
} from "react-hook-form";

import { EntityAutocomplete, type EntityAutocompleteProps } from "../EntityAutocomplete";

type FormAutocompleteProps<T extends FieldValues> = {
  control: Control<T>;
  name: FieldPath<T>;
  rules?: RegisterOptions<T, FieldPath<T>>;
} & Omit<EntityAutocompleteProps, "value" | "onChange" | "error" | "helperText" | "onBlur">;

export function FormAutocomplete<T extends FieldValues>({
  control,
  name,
  rules,
  ...props
}: FormAutocompleteProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      rules={rules}
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
