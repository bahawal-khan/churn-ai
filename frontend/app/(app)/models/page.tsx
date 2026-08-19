"use client";

import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { isModelActive, modelsApi, type ModelSummary } from "@/lib/api/models";
import { formatDate, formatPercent, titleCase } from "@/lib/utils";

export default function ModelsPage() {
  const models = useSWR("models-list", () => modelsApi.list());
  const { showToast } = useToast();
  const [confirmTarget, setConfirmTarget] = useState<{ model: ModelSummary; action: "activate" | "deactivate" } | null>(null);

  async function handleConfirm() {
    if (!confirmTarget || typeof confirmTarget.model.model_id !== "number") return;
    if (confirmTarget.action === "activate") {
      await modelsApi.activate(confirmTarget.model.model_id);
      showToast("Model activated.", "success");
    } else {
      await modelsApi.deactivate(confirmTarget.model.model_id);
      showToast("Model deactivated.", "success");
    }
    models.mutate();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Model Management</h1>
        <p className="text-sm text-text-muted">The shared baseline model plus every company-specific model you&apos;ve trained.</p>
      </div>

      <Card>
        {models.error ? (
          <ErrorState error={models.error} onRetry={() => models.mutate()} />
        ) : !models.data ? (
          <TableSkeleton rows={4} columns={5} />
        ) : models.data.length === 0 ? (
          <EmptyState title="No models available" description="No model artifacts have been found yet." />
        ) : (
          <ul className="flex flex-col divide-y divide-border-subtle">
            {models.data.map((model) => {
              const active = isModelActive(model);
              const isCompanySpecific = model.model_type === "company_specific";
              return (
                <li key={model.model_id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <Link href={`/models/${model.model_id}`} className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-text-primary">
                        {titleCase(model.algorithm)} {model.version ? `v${model.version}` : ""}
                      </p>
                      <Badge tone="neutral">{model.model_type === "baseline_global" ? "Baseline" : "Company"}</Badge>
                      {active && <Badge tone="success">Active</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-text-muted">
                      ROC-AUC {formatPercent(model.validation_metrics_summary?.roc_auc ?? null)} · Trained{" "}
                      {formatDate(model.created_at)}
                    </p>
                  </Link>
                  {isCompanySpecific && (
                    <Button
                      size="sm"
                      variant={active ? "secondary" : "primary"}
                      onClick={() => setConfirmTarget({ model, action: active ? "deactivate" : "activate" })}
                    >
                      {active ? "Deactivate" : "Activate"}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      {confirmTarget && (
        <ConfirmDialog
          open={Boolean(confirmTarget)}
          onClose={() => setConfirmTarget(null)}
          onConfirm={handleConfirm}
          title={confirmTarget.action === "activate" ? "Activate this model?" : "Deactivate this model?"}
          description={
            confirmTarget.action === "activate"
              ? "This will replace the currently active model for every future prediction in your organization."
              : "This will fall back to the shared baseline model for future predictions."
          }
          confirmLabel={confirmTarget.action === "activate" ? "Activate" : "Deactivate"}
          danger={confirmTarget.action === "deactivate"}
        />
      )}
    </div>
  );
}
