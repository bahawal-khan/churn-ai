"use client";

import { useState } from "react";
import useSWR from "swr";

import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { ColumnMappingPanel } from "@/components/upload/ColumnMappingPanel";
import { DataQualityReportPanel } from "@/components/upload/DataQualityReportPanel";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { datasetsApi, type DatasetUploadResult } from "@/lib/api/datasets";
import { formatDate, formatNumber } from "@/lib/utils";

export default function UploadPage() {
  const [result, setResult] = useState<DatasetUploadResult | null>(null);
  const history = useSWR("upload-history", () => datasetsApi.list(1, 10));
  const { showToast } = useToast();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Upload Data</h1>
        <p className="text-sm text-text-muted">
          Upload a CSV of customer data. ChurnAI validates it and shows a data quality report before you use it.
        </p>
      </div>

      <Card>
        <UploadDropzone
          onUpload={(file, onProgress) => datasetsApi.upload(file, undefined, onProgress)}
          onSuccess={(res) => {
            setResult(res);
            showToast("Upload complete.", "success");
            history.mutate();
          }}
        />
      </Card>

      {result && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Preview</CardTitle>
            </CardHeader>
            <div className="scrollbar-thin overflow-x-auto">
              <table className="w-full min-w-[560px] border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border-subtle text-left text-text-muted">
                    {result.dataset.column_schema.slice(0, 8).map((c) => (
                      <th key={c.name} className="px-2 py-1.5 font-semibold">
                        {c.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {result.preview.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                      {result.dataset.column_schema.slice(0, 8).map((c) => (
                        <td key={c.name} className="px-2 py-1.5 text-text-primary">
                          {String(row[c.name] ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Column Mapping</CardTitle>
            </CardHeader>
            <ColumnMappingPanel uploadedColumns={result.dataset.column_schema.map((c) => c.name)} />
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data Quality Report</CardTitle>
            </CardHeader>
            <DataQualityReportPanel report={result.quality_report} />
            <div className="mt-4 flex flex-wrap gap-2">
              {result.dataset.has_target_column ? (
                <Badge tone="success">Includes a churn/outcome column — can be used for training</Badge>
              ) : (
                <Badge tone="neutral">No outcome column detected — can be used for predictions only</Badge>
              )}
            </div>
          </Card>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Upload History</CardTitle>
        </CardHeader>
        {history.error ? (
          <ErrorState error={history.error} onRetry={() => history.mutate()} />
        ) : !history.data ? (
          <TableSkeleton rows={4} columns={4} />
        ) : (
          <DataTable
            rows={history.data.data}
            getRowId={(d) => d.id}
            emptyMessage="No uploads yet — upload a CSV above to get started."
            columns={[
              { key: "filename", header: "File", render: (d) => d.original_filename },
              { key: "source", header: "Type", render: (d) => d.source_type.replace(/_/g, " ") },
              { key: "rows", header: "Rows", render: (d) => formatNumber(d.row_count) },
              {
                key: "target",
                header: "Trainable",
                render: (d) => (d.has_target_column ? <Badge tone="success">Yes</Badge> : <Badge tone="neutral">No</Badge>),
              },
              { key: "created_at", header: "Uploaded", render: (d) => formatDate(d.created_at), sortValue: (d) => d.created_at },
            ]}
          />
        )}
      </Card>
    </div>
  );
}
