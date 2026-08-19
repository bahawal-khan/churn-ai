"use client";

import { useState } from "react";
import useSWR from "swr";

import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { REPORT_TYPES, reportsApi, type ReportType } from "@/lib/api/reports";
import { formatDateTime, formatNumber } from "@/lib/utils";

export default function ReportsPage() {
  const reports = useSWR("reports-list", () => reportsApi.list(1, 20));
  const { showToast } = useToast();
  const [generating, setGenerating] = useState<ReportType | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  async function handleGenerate(type: ReportType) {
    setGenerating(type);
    try {
      await reportsApi.generate(type);
      showToast("Report generated.", "success");
      reports.mutate();
    } catch {
      showToast("Failed to generate report. Please try again.", "error");
    } finally {
      setGenerating(null);
    }
  }

  async function handleDownload(reportId: string) {
    setDownloadingId(reportId);
    try {
      const blob = await reportsApi.download(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `churnai_report_${reportId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      showToast("Download failed. Please try again.", "error");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Reports</h1>
        <p className="text-sm text-text-muted">Generate exportable CSV summaries of your predictions and customers.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {REPORT_TYPES.map((type) => (
          <Card key={type.value} className="flex flex-col gap-3">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">{type.label}</h3>
              <p className="mt-1 text-xs text-text-muted">{type.description}</p>
            </div>
            <Button
              size="sm"
              className="self-start"
              loading={generating === type.value}
              onClick={() => handleGenerate(type.value)}
            >
              Generate
            </Button>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generated Reports</CardTitle>
        </CardHeader>
        {reports.error ? (
          <ErrorState error={reports.error} onRetry={() => reports.mutate()} />
        ) : !reports.data ? (
          <TableSkeleton rows={3} columns={4} />
        ) : (
          <DataTable
            rows={reports.data.data}
            getRowId={(r) => r.id}
            emptyMessage="No reports generated yet."
            columns={[
              { key: "type", header: "Type", render: (r) => REPORT_TYPES.find((t) => t.value === r.report_type)?.label ?? r.report_type },
              { key: "rows", header: "Rows", render: (r) => formatNumber(r.row_count) },
              { key: "created_at", header: "Generated", render: (r) => formatDateTime(r.created_at), sortValue: (r) => r.created_at },
              {
                key: "download",
                header: "",
                render: (r) => (
                  <Button size="sm" variant="secondary" loading={downloadingId === r.id} onClick={() => handleDownload(r.id)}>
                    Download
                  </Button>
                ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  );
}
