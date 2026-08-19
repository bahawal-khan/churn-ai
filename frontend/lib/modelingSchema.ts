/** Mirrors `ml/config.py::MODELING_COLUMNS` exactly — used client-side to
 * build a read-only "detected column mapping" preview
 * (`docs/PROJECT_SPEC.md` §16.1) since the backend has no mapping-edit
 * endpoint to persist user corrections to yet (`backend/services/
 * dataset_service.py`'s own documented Phase-9 gap: "column_mapping is left
 * NULL until the mapping-confirmation UI exists"). This Phase 10 UI shows
 * the auto-detected mapping for user confirmation but cannot yet persist
 * edits — a known, documented limitation, not silently hidden. */
export const MODELING_COLUMNS = [
  "Gender",
  "Senior Citizen",
  "Partner",
  "Dependents",
  "Tenure Months",
  "Phone Service",
  "Multiple Lines",
  "Internet Service",
  "Online Security",
  "Online Backup",
  "Device Protection",
  "Tech Support",
  "Streaming TV",
  "Streaming Movies",
  "Contract",
  "Paperless Billing",
  "Payment Method",
  "Monthly Charges",
  "Total Charges",
];

function normalize(name: string): string {
  return name.trim().toLowerCase();
}

export interface ColumnMappingEntry {
  schemaColumn: string;
  matchedColumn: string | null;
}

export function buildDetectedMapping(uploadedColumns: string[]): {
  matched: ColumnMappingEntry[];
  unmapped: string[];
} {
  const byNormalized = new Map(uploadedColumns.map((c) => [normalize(c), c]));
  const matched = MODELING_COLUMNS.map((schemaColumn) => ({
    schemaColumn,
    matchedColumn: byNormalized.get(normalize(schemaColumn)) ?? null,
  }));
  const usedColumns = new Set(matched.map((m) => m.matchedColumn).filter(Boolean));
  const unmapped = uploadedColumns.filter((c) => !usedColumns.has(c));
  return { matched, unmapped };
}
