import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/Table";
import type { MetricSummary } from "@/lib/api/models";
import { formatPercent } from "@/lib/utils";

const METRIC_ROWS: { key: keyof MetricSummary; label: string }[] = [
  { key: "accuracy", label: "Accuracy" },
  { key: "precision", label: "Precision" },
  { key: "recall", label: "Recall" },
  { key: "f1", label: "F1 Score" },
  { key: "roc_auc", label: "ROC-AUC" },
  { key: "pr_auc", label: "PR-AUC" },
];

/** Full metric suite (`docs/ML_SPEC.md` §12), used in the Train workflow's
 * Review Metrics step, Model detail, and Analytics' model comparison. */
export function MetricsTable({
  validation,
  test,
}: {
  validation: MetricSummary | null;
  test?: MetricSummary | null;
}) {
  return (
    <Table>
      <Thead>
        <Tr>
          <Th>Metric</Th>
          <Th>Validation</Th>
          {test !== undefined && <Th>Test</Th>}
        </Tr>
      </Thead>
      <Tbody>
        {METRIC_ROWS.map((row) => (
          <Tr key={row.key}>
            <Td className="font-medium">{row.label}</Td>
            <Td>{validation ? formatPercent(validation[row.key] as number) : "—"}</Td>
            {test !== undefined && <Td>{test ? formatPercent(test[row.key] as number) : "—"}</Td>}
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
}
