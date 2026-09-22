import { Autocomplete, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useDebouncedValue } from "../../shared/lib/useDebouncedValue";
import { queryKeys } from "../../shared/lookups/queryKeys";
import { fetchStockItems } from "./api";
import type { StockItem } from "./labels";

export const stockItemLabel = (item: StockItem) =>
  `${item.name} · ${item.location_name} · остаток ${item.quantity} ${item.unit}`;

interface StockItemPickerProps {
  label?: string;
  value: StockItem | null;
  onChange: (item: StockItem | null) => void;
  /** Только позиции с остатком > 0 (для выдачи). */
  onlyAvailable?: boolean;
  /** Уже выбранные в других строках позиции — не предлагаются. */
  excludeIds?: ReadonlySet<number>;
  error?: string;
}

/** Выбор активной позиции расходников с поиском на сервере. */
export function StockItemPicker({
  label = "Позиция",
  value,
  onChange,
  onlyAvailable = false,
  excludeIds,
  error,
}: StockItemPickerProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input);
  const options = useQuery({
    queryKey: [...queryKeys.stock, "picker-options", query],
    queryFn: () => fetchStockItems({ q: query, limit: 50, offset: 0 }),
    enabled: open,
  });
  const items = (options.data?.items ?? []).filter(
    (item) => (!onlyAvailable || item.quantity > 0) && !excludeIds?.has(item.id),
  );

  return (
    <Autocomplete<StockItem>
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      value={value}
      options={items}
      loading={options.isFetching}
      filterOptions={(list) => list}
      isOptionEqualToValue={(option, current) => option.id === current.id}
      getOptionLabel={stockItemLabel}
      onChange={(_, item) => onChange(item)}
      onInputChange={(_, text, reason) => {
        if (reason === "input") setInput(text);
        if (reason === "clear" || reason === "reset") setInput("");
      }}
      noOptionsText={onlyAvailable ? "Нет позиций с остатком" : "Ничего не найдено"}
      loadingText="Загрузка…"
      renderInput={(params) => (
        <TextField {...params} label={label} error={Boolean(error)} helperText={error} />
      )}
    />
  );
}
