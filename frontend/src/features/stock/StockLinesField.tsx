import { Box, Button, IconButton, Stack, TextField } from "@mui/material";
import { IconPlus, IconTrash } from "@tabler/icons-react";

import type { StockItem } from "./labels";
import { StockItemPicker } from "./StockItemPicker";

export interface StockLineValue {
  /** Ключ строки для React: позиции в строке может ещё не быть. */
  key: number;
  item: StockItem | null;
  quantity: string;
}

/** Ошибка строки, видимая до отправки: не выбрана позиция, неверное количество, мало остатка. */
export function stockLineError(line: StockLineValue): string | null {
  if (!line.item) return "Выберите позицию";
  if (!/^\d{1,7}$/.test(line.quantity.trim()) || Number(line.quantity) < 1) {
    return "Целое число от 1";
  }
  if (Number(line.quantity) > line.item.quantity) {
    return `Доступно ${line.item.quantity} ${line.item.unit}`;
  }
  return null;
}

let nextKey = 1;

export function newStockLine(): StockLineValue {
  return { key: nextKey++, item: null, quantity: "" };
}

interface StockLinesFieldProps {
  value: StockLineValue[];
  onChange: (lines: StockLineValue[]) => void;
  /** Остаток на сервере для строк, отклонённых ответом 409 (null — позиция не найдена). */
  unavailable: ReadonlyMap<number, number | null>;
  /** Показывать ошибки строк (после попытки отправки). */
  showErrors: boolean;
  maxLines: number;
}

/** Строки «позиция + количество» для единой выдачи. */
export function StockLinesField({
  value,
  onChange,
  unavailable,
  showErrors,
  maxLines,
}: StockLinesFieldProps) {
  const update = (key: number, patch: Partial<StockLineValue>) =>
    onChange(value.map((line) => (line.key === key ? { ...line, ...patch } : line)));

  const serverHint = (line: StockLineValue) => {
    if (!line.item || !unavailable.has(line.item.id)) return null;
    const available = unavailable.get(line.item.id);
    return available === null || available === undefined
      ? "Позиция недоступна"
      : `На складе осталось ${available} ${line.item.unit}`;
  };

  return (
    <Stack spacing={1.5}>
      {value.map((line) => {
        const chosen = new Set(
          value.filter((other) => other.key !== line.key && other.item).map((o) => o.item!.id),
        );
        const hint = serverHint(line) ?? (showErrors ? stockLineError(line) : null);
        return (
          <Stack key={line.key} direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Box sx={{ flex: 1 }}>
              <StockItemPicker
                label="Расходник"
                value={line.item}
                onChange={(item) => update(line.key, { item })}
                onlyAvailable
                excludeIds={chosen}
                error={showErrors && !line.item ? "Выберите позицию" : undefined}
              />
            </Box>
            <TextField
              label="Количество"
              value={line.quantity}
              onChange={(event) => update(line.key, { quantity: event.target.value })}
              error={Boolean(hint) && Boolean(line.item)}
              helperText={line.item ? hint : undefined}
              sx={{ width: { sm: 180 } }}
              slotProps={{ htmlInput: { inputMode: "numeric" } }}
            />
            <IconButton
              aria-label="Удалить строку"
              onClick={() => onChange(value.filter((other) => other.key !== line.key))}
              sx={{ alignSelf: { sm: "flex-start" }, mt: { sm: 1 } }}
            >
              <IconTrash size={18} />
            </IconButton>
          </Stack>
        );
      })}
      <Box>
        <Button
          startIcon={<IconPlus size={18} />}
          disabled={value.length >= maxLines}
          onClick={() => onChange([...value, newStockLine()])}
        >
          Добавить расходник
        </Button>
      </Box>
    </Stack>
  );
}
