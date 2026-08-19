import { Badge } from "@/components/ui/Badge";
import { buildDetectedMapping } from "@/lib/modelingSchema";

/** Read-only detected-mapping preview (`docs/PROJECT_SPEC.md` §16.1). The
 * backend doesn't yet expose an endpoint to persist an edited mapping, so
 * this is confirmation/visibility only, not an editable-and-saved mapping —
 * flagged in the plan, not silently hidden from the user either: the note
 * below says so explicitly. */
export function ColumnMappingPanel({ uploadedColumns }: { uploadedColumns: string[] }) {
  const { matched, unmapped } = buildDetectedMapping(uploadedColumns);
  const matchedCount = matched.filter((m) => m.matchedColumn).length;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-text-muted">
        Detected {matchedCount} of {matched.length} required columns automatically, by matching column names. Column
        mapping is not yet editable in this release — re-upload with matching column names if any are missing.
      </p>
      <ul className="flex flex-col divide-y divide-border-subtle rounded-card border border-border-subtle">
        {matched.map((entry) => (
          <li key={entry.schemaColumn} className="flex items-center justify-between gap-3 p-2.5 text-sm">
            <span className="text-text-primary">{entry.schemaColumn}</span>
            {entry.matchedColumn ? (
              <span className="flex items-center gap-2 text-text-muted">
                ← {entry.matchedColumn}
                <Badge tone="success">Matched</Badge>
              </span>
            ) : (
              <Badge tone="danger">Not found</Badge>
            )}
          </li>
        ))}
      </ul>
      {unmapped.length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-muted">Uploaded columns not used by the model:</p>
          <p className="mt-1 text-xs text-text-muted">{unmapped.join(", ")}</p>
        </div>
      )}
    </div>
  );
}
