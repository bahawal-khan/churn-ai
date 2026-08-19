"use client";

import { useMemo, useState } from "react";

import { RiskBadge } from "@/components/common/RiskBadge";
import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { predictionsApi, type BatchPredictionResult, type BatchPredictionRow } from "@/lib/api/predictions";
import { formatNumber, formatPercent, toCsv } from "@/lib/utils";

interface FieldError {
  field: string;
  message: string;
}

/** Splits a backend `prediction_error` string (`"Field: message; Field2:
 * message2"`, `backend/services/prediction_service.py`) into per-field
 * parts so the UI can render a scannable list instead of one dense
 * run-on sentence. */
function parseFieldErrors(predictionError: string | null): FieldError[] {
  if (!predictionError) return [];
  return predictionError.split("; ").map((segment) => {
    const separatorIndex = segment.indexOf(": ");
    return separatorIndex === -1
      ? { field: "", message: segment }
      : { field: segment.slice(0, separatorIndex), message: segment.slice(separatorIndex + 2) };
  });
}

/** Rows usually fail the same *rule* (e.g. "Contract" isn't one of the
 * allowed values) with a different literal bad value each time — strip the
 * "got 'X'" part so rows with different bad values still group under one
 * rule instead of each producing their own one-row entry. */
function ruleOnly(message: string): string {
  const gotIndex = message.indexOf(", got ");
  return gotIndex === -1 ? message : `${message.slice(0, gotIndex)}.`;
}

/** Aggregates every failed row's field errors into "N rows — Field: reason"
 * entries, so a file where e.g. 8 rows all have some bad "Contract" value
 * shows one actionable line instead of 8 repeats of near-identical text. */
function summarizeFieldErrors(results: BatchPredictionRow[]): Array<FieldError & { rowCount: number }> {
  const counts = new Map<string, { field: string; message: string; rowCount: number }>();
  for (const row of results) {
    for (const { field, message } of parseFieldErrors(row.prediction_error)) {
      const generalMessage = ruleOnly(message);
      const key = `${field} ${generalMessage}`;
      const existing = counts.get(key);
      if (existing) {
        existing.rowCount += 1;
      } else {
        counts.set(key, { field, message: generalMessage, rowCount: 1 });
      }
    }
  }
  return Array.from(counts.values()).sort((a, b) => b.rowCount - a.rowCount);
}

export function BatchPredictionPanel() {
  const [result, setResult] = useState<BatchPredictionResult | null>(null);
  const { showToast } = useToast();

  const fieldIssues = useMemo(() => (result ? summarizeFieldErrors(result.results) : []), [result]);

  function handleDownload() {
    if (!result) return;
    try {
      const csv = toCsv(result.results);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `churnai_batch_${result.batch_job_id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      showToast("Download failed. Please try again.", "error");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <UploadDropzone
          label="Drag & drop a CSV of customers to score, or click to browse"
          onUpload={(file, onProgress) => predictionsApi.predictBatch(file, onProgress)}
          onSuccess={(res) => {
            setResult(res);
            if (res.summary.scored_rows === 0) {
              showToast("No rows could be scored — every row failed validation. See details below.", "error");
            } else if (res.summary.failed_rows > 0) {
              showToast(`Batch prediction complete — ${res.summary.failed_rows} row(s) need fixing.`, "success");
            } else {
              showToast("Batch prediction complete.", "success");
            }
          }}
        />
      </Card>

      {result && (
        <>
          {result.summary.scored_rows === 0 && (
            <div className="rounded-card border border-danger/30 bg-danger-soft p-4 text-sm">
              <p className="font-semibold text-danger">No rows could be scored</p>
              <p className="mt-1 text-text-primary">
                Every row in this file failed validation — the probability and risk columns are empty because
                nothing was actually predicted. This isn&apos;t a bug: the values in your file don&apos;t match what
                the model expects. See <span className="font-semibold">&quot;Why rows failed&quot;</span> below for
                exactly which columns and values to fix, then re-upload.
              </p>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <SummaryStat label="Total Rows" value={formatNumber(result.summary.total_rows)} />
              <SummaryStat label="Scored" value={formatNumber(result.summary.scored_rows)} />
              <SummaryStat label="Predicted Churners" value={formatNumber(result.summary.predicted_churners)} tone="danger" />
              <SummaryStat label="Failed Rows" value={formatNumber(result.summary.failed_rows)} tone={result.summary.failed_rows > 0 ? "warning" : "default"} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="success">Low: {result.summary.risk_level_counts.low}</Badge>
              <Badge tone="warning">Medium: {result.summary.risk_level_counts.medium}</Badge>
              <Badge tone="danger">High: {result.summary.risk_level_counts.high}</Badge>
            </div>
            <Button className="mt-4" size="sm" onClick={handleDownload}>
              Download Results CSV
            </Button>
          </Card>

          {fieldIssues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Why rows failed</CardTitle>
              </CardHeader>
              <p className="mb-3 text-xs text-text-muted">
                These uploaded values don&apos;t match what the model expects — fix them in your source file and
                re-upload. Rows with any other error were scored normally.
              </p>
              <ul className="flex flex-col gap-2">
                {fieldIssues.map((issue, i) => (
                  <li key={i} className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge tone="danger">{`${issue.rowCount} row${issue.rowCount === 1 ? "" : "s"}`}</Badge>
                    <span className="font-semibold text-text-primary">{issue.field}</span>
                    <span className="text-text-muted">{issue.message}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Results ({result.results.length})</CardTitle>
            </CardHeader>
            <DataTable
              rows={result.results.slice(0, 100)}
              getRowId={(_r, i) => i}
              emptyMessage="No rows scored."
              rowClassName={(r) => (r.prediction_error ? "bg-danger-soft/40" : undefined)}
              columns={[
                {
                  key: "probability",
                  header: "Probability",
                  render: (r) => (r.churn_probability !== null ? formatPercent(r.churn_probability) : "—"),
                  sortValue: (r) => r.churn_probability,
                },
                { key: "risk", header: "Risk", render: (r) => <RiskBadge level={r.risk_level} /> },
                {
                  key: "error",
                  header: "Error",
                  render: (r) =>
                    r.prediction_error ? (
                      <ul className="flex flex-col gap-0.5">
                        {parseFieldErrors(r.prediction_error).map((e, i) => (
                          <li key={i} className="text-xs text-danger">
                            {e.field && <span className="font-semibold">{e.field}: </span>}
                            {e.message}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      "—"
                    ),
                },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  );
}

function SummaryStat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <div>
      <p className="text-xs text-text-muted">{label}</p>
      <p
        className={`text-xl font-bold ${tone === "danger" ? "text-risk-high" : tone === "warning" ? "text-risk-medium" : "text-text-primary"}`}
      >
        {value}
      </p>
    </div>
  );
}
