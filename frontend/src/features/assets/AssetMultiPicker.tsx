import { Autocomplete, Chip, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useDebouncedValue } from "../../shared/lib/useDebouncedValue";
import { queryKeys } from "../../shared/lookups/queryKeys";
import { fetchAssets } from "./api";
import type { Asset } from "./labels";

interface AssetMultiPickerProps {
  value: Asset[];
  onChange: (assets: Asset[]) => void;
  /** Активы, которые стали недоступны (ответ 409): подсвечиваются красным. */
  unavailableIds: ReadonlySet<number>;
  error?: string;
}

const assetLabel = (asset: Asset) => `${asset.inventory_number} — ${asset.model}`;

/** Выбор нескольких активов со статусом «На складе» с поиском на сервере. */
export function AssetMultiPicker({
  value,
  onChange,
  unavailableIds,
  error,
}: AssetMultiPickerProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input);
  const options = useQuery({
    queryKey: [...queryKeys.assets, "in-stock-options", query],
    queryFn: () => fetchAssets({ q: query, status: "in_stock", limit: 50, offset: 0 }),
    enabled: open,
  });

  return (
    <Autocomplete<Asset, true>
      multiple
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      value={value}
      options={options.data?.items ?? []}
      loading={options.isFetching}
      filterOptions={(items) => items}
      filterSelectedOptions
      isOptionEqualToValue={(option, current) => option.id === current.id}
      getOptionLabel={assetLabel}
      onChange={(_, assets) => onChange(assets)}
      onInputChange={(_, text, reason) => {
        if (reason === "input") setInput(text);
        if (reason === "clear" || reason === "reset") setInput("");
      }}
      noOptionsText="Свободной техники не найдено"
      loadingText="Загрузка…"
      renderValue={(assets, getItemProps) =>
        assets.map((asset, index) => {
          const { key, ...itemProps } = getItemProps({ index });
          return (
            <Chip
              key={key}
              {...itemProps}
              label={assetLabel(asset)}
              color={unavailableIds.has(asset.id) ? "error" : "default"}
            />
          );
        })
      }
      renderInput={(params) => (
        <TextField {...params} label="Техника" error={Boolean(error)} helperText={error} />
      )}
    />
  );
}
