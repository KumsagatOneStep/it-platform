import { Chip } from "@mui/material";

import { STATUS_COLORS, STATUS_LABELS, type AssetStatus } from "./labels";

export function AssetStatusChip({ status }: { status: AssetStatus }) {
  return <Chip size="small" label={STATUS_LABELS[status]} color={STATUS_COLORS[status]} />;
}
