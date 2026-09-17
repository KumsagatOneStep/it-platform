import { FormControlLabel, Switch } from "@mui/material";
import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

interface FormSwitchProps<T extends FieldValues> {
  control: Control<T>;
  name: FieldPath<T>;
  label: string;
}

export function FormSwitch<T extends FieldValues>({ control, name, label }: FormSwitchProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <FormControlLabel
          label={label}
          control={
            <Switch
              name={field.name}
              checked={Boolean(field.value)}
              onChange={(event) => field.onChange(event.target.checked)}
            />
          }
        />
      )}
    />
  );
}
