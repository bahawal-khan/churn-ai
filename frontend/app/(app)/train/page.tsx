"use client";

import { useState } from "react";
import useSWR from "swr";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { ProgressStepper, type StepStatus } from "@/components/ui/ProgressStepper";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { MetricsTable } from "@/components/models/MetricsTable";
import { datasetsApi } from "@/lib/api/datasets";
import { modelsApi } from "@/lib/api/models";
import { trainingApi, TERMINAL_TRAINING_STATUSES, type TrainingJob, type TrainingJobStatus } from "@/lib/api/training";
import { ApiError } from "@/lib/api/client";
import { formatDateTime, titleCase } from "@/lib/utils";

const STEPS = [
  { key: "select", label: "Select Dataset" },
  { key: "target", label: "Target Column" },
  { key: "train", label: "Train & Evaluate" },
  { key: "activate", label: "Review & Activate" },
];

const STATUS_ORDER: TrainingJobStatus[] = ["queued", "validating", "preprocessing", "training", "evaluating", "completed"];

export default function TrainPage() {
  const datasets = useSWR("train-datasets", () => datasetsApi.list(1, 50));
  const jobs = useSWR("train-jobs", () => trainingApi.list(1, 10));
  const { showToast } = useToast();

  const [datasetId, setDatasetId] = useState<string>("");
  const [targetColumn, setTargetColumn] = useState<string>("");
  const [job, setJob] = useState<TrainingJob | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<ApiError | null>(null);
  const [activateOpen, setActivateOpen] = useState(false);

  const selectedDataset = datasets.data?.data.find((d) => String(d.id) === datasetId) ?? null;

  async function handleStartTraining() {
    if (!selectedDataset || !targetColumn) return;
    setStarting(true);
    setStartError(null);
    try {
      const created = await trainingApi.start(selectedDataset.id, targetColumn);
      setJob(created);
      if (TERMINAL_TRAINING_STATUSES.includes(created.status)) {
        jobs.mutate();
      } else {
        pollJob(created.id);
      }
    } catch (err) {
      setStartError(err instanceof ApiError ? err : null);
    } finally {
      setStarting(false);
    }
  }

  function pollJob(jobId: number) {
    const interval = setInterval(async () => {
      const latest = await trainingApi.get(jobId);
      setJob(latest);
      if (TERMINAL_TRAINING_STATUSES.includes(latest.status)) {
        clearInterval(interval);
        jobs.mutate();
      }
    }, 2000);
  }

  async function handleActivate() {
    if (!job?.resulting_model_id) return;
    await modelsApi.activate(job.resulting_model_id);
    showToast("Model activated.", "success");
  }

  const currentStepIndex = !job ? (targetColumn ? 1 : 0) : job.status === "completed" ? 3 : 2;

  function statusFor(key: string, index: number): StepStatus {
    if (index < currentStepIndex) return "done";
    if (index === currentStepIndex) return job?.status === "failed" ? "failed" : "active";
    return "pending";
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Train Model</h1>
        <p className="text-sm text-text-muted">
          Train a company-specific churn model on your own historical data with known outcomes.
        </p>
      </div>

      <Card>
        <ProgressStepper steps={STEPS} statusFor={statusFor} />
      </Card>

      {!job && (
        <Card>
          <CardHeader>
            <CardTitle>1. Select a dataset and target column</CardTitle>
          </CardHeader>
          {datasets.error ? (
            <ErrorState error={datasets.error} onRetry={() => datasets.mutate()} />
          ) : !datasets.data ? (
            <TableSkeleton rows={2} columns={2} />
          ) : datasets.data.data.length === 0 ? (
            <p className="text-sm text-text-muted">
              No datasets uploaded yet.{" "}
              <a href="/upload" className="text-accent-primary hover:underline">
                Upload one first
              </a>
              .
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              <Select
                label="Dataset"
                placeholder="Choose a dataset…"
                value={datasetId}
                onChange={(e) => {
                  setDatasetId(e.target.value);
                  setTargetColumn("");
                }}
                options={datasets.data.data.map((d) => ({
                  value: String(d.id),
                  label: `${d.original_filename} (${d.row_count} rows)`,
                }))}
              />
              {selectedDataset && (
                <Select
                  label="Target column (historical churn outcome)"
                  placeholder="Choose the outcome column…"
                  value={targetColumn}
                  onChange={(e) => setTargetColumn(e.target.value)}
                  options={selectedDataset.column_schema.map((c) => ({ value: c.name, label: c.name }))}
                  hint="ChurnAI never guesses this — pick the column that records which customers historically churned."
                />
              )}
              {startError && (
                <div className="rounded-control bg-danger-soft p-3 text-sm text-danger">
                  <p>{startError.message}</p>
                  {startError.code === "TRAINING_LABELS_REQUIRED" && (
                    <p className="mt-1">
                      You can still use the baseline model for predictions —{" "}
                      <a href="/predict" className="underline">
                        go to Predictions
                      </a>
                      .
                    </p>
                  )}
                </div>
              )}
              <Button
                onClick={handleStartTraining}
                disabled={!datasetId || !targetColumn}
                loading={starting}
                className="self-start"
              >
                Start Training
              </Button>
            </div>
          )}
        </Card>
      )}

      {job && (
        <Card>
          <CardHeader>
            <CardTitle>Training Job #{job.id}</CardTitle>
          </CardHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
              {STATUS_ORDER.map((status) => (
                <Badge
                  key={status}
                  tone={
                    job.status === "failed" && status === "training"
                      ? "danger"
                      : STATUS_ORDER.indexOf(job.status) >= STATUS_ORDER.indexOf(status)
                        ? "accent"
                        : "neutral"
                  }
                >
                  {titleCase(status)}
                </Badge>
              ))}
            </div>
            {job.status_message && <p className="text-sm text-text-muted">{job.status_message}</p>}

            {job.status === "failed" && (
              <div className="rounded-control bg-danger-soft p-3 text-sm text-danger">Training failed. See the message above for details.</div>
            )}

            {job.status === "completed" && job.resulting_model_id && (
              <CompletedModelReview modelId={job.resulting_model_id} onActivate={() => setActivateOpen(true)} />
            )}

            {!TERMINAL_TRAINING_STATUSES.includes(job.status) && (
              <p className="text-sm text-text-muted">Training in progress — this page updates automatically…</p>
            )}

            <Button
              variant="secondary"
              size="sm"
              className="self-start"
              onClick={() => {
                setJob(null);
                setDatasetId("");
                setTargetColumn("");
              }}
            >
              Start another training run
            </Button>
          </div>
        </Card>
      )}

      {job?.resulting_model_id && (
        <ConfirmDialog
          open={activateOpen}
          onClose={() => setActivateOpen(false)}
          onConfirm={handleActivate}
          title="Activate this model?"
          description="Activating this model will make it the model used for every future prediction in your organization, replacing the current active model."
          confirmLabel="Activate"
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Training History</CardTitle>
        </CardHeader>
        {jobs.error ? (
          <ErrorState error={jobs.error} onRetry={() => jobs.mutate()} />
        ) : !jobs.data ? (
          <TableSkeleton rows={3} columns={3} />
        ) : (
          <DataTable
            rows={jobs.data.data}
            getRowId={(j) => j.id}
            emptyMessage="No training runs yet."
            columns={[
              { key: "id", header: "Job", render: (j) => `#${j.id}` },
              {
                key: "status",
                header: "Status",
                render: (j) => <Badge tone={j.status === "completed" ? "success" : j.status === "failed" ? "danger" : "accent"}>{titleCase(j.status)}</Badge>,
              },
              { key: "created_at", header: "Started", render: (j) => formatDateTime(j.created_at), sortValue: (j) => j.created_at },
            ]}
          />
        )}
      </Card>
    </div>
  );
}

function CompletedModelReview({ modelId, onActivate }: { modelId: number; onActivate: () => void }) {
  const detail = useSWR(`train-model-detail-${modelId}`, () => modelsApi.get(modelId));

  if (detail.error) return <ErrorState error={detail.error} onRetry={() => detail.mutate()} />;
  if (!detail.data) return <TableSkeleton rows={3} columns={2} />;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm font-medium text-text-primary">
        Winning algorithm: {titleCase(detail.data.metadata.algorithm)}
      </p>
      <MetricsTable validation={detail.data.metrics?.validation ?? null} test={detail.data.metrics?.test} />
      <Button onClick={onActivate} className="self-start">
        Activate this model
      </Button>
    </div>
  );
}
