import { TextField, type TextFieldProps } from "@mui/material";
import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
  type RegisterOptions,
} from "react-hook-form";

type FormTextFieldProps<T extends FieldValues, N extends FieldPath<T>> = {
  control: Control<T>;
  name: N;
  rules?: RegisterOptions<T, N>;
} & Omit<TextFieldProps, "name" | "value" | "onChange" | "onBlur" | "error" | "defaultValue">;

export function FormTextField<T extends FieldValues, N extends FieldPath<T>>({
  control,
  name,
  rules,
  helperText,
  ...props
}: FormTextFieldProps<T, N>) {
  return (
    <Controller
      control={control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => (
        <TextField
          {...props}
          name={field.name}
          inputRef={field.ref}
          value={field.value ?? ""}
          onChange={field.onChange}
          onBlur={field.onBlur}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message ?? helperText}
          fullWidth
        />
      )}
    />
  );
}
