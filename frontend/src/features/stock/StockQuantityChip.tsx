import { Chip } from "@mui/material";

import type { StockItem } from "./labels";

/** Остаток с единицей; ниже минимума — красным. */
export function StockQuantityChip({ item }: { item: StockItem }) {
  return (
    <Chip
      size="small"
      label={`${item.quantity} ${item.unit}`}
      color={item.is_low ? "error" : "default"}
      variant={item.is_low ? "filled" : "outlined"}
    />
  );
}
