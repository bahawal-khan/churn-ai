"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { RiskBadge } from "@/components/common/RiskBadge";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ShapForcePlot } from "@/components/predict/ShapForcePlot";
import { customersApi } from "@/lib/api/customers";
import { formatDateTime, formatPercent, titleCase } from "@/lib/utils";

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const customerId = Number(params.id);
  const detail = useSWR(`customer-${customerId}`, () => customersApi.get(customerId));
  const [expanded, setExpanded] = useState<number | null>(null);

  if (detail.error) return <ErrorState error={detail.error} onRetry={() => detail.mutate()} />;
  if (!detail.data) return <TableSkeleton rows={6} columns={3} />;

  const { customer, predictions } = detail.data;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            {customer.external_customer_id ?? `Customer #${customer.id}`}
          </h1>
          <p className="text-sm text-text-muted">Added {formatDateTime(customer.created_at)}</p>
        </div>
        <RiskBadge level={customer.latest_risk_level} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
          {Object.entries(customer.feature_data).map(([key, value]) => (
            <div key={key}>
              <dt className="text-xs text-text-muted">{titleCase(key)}</dt>
              <dd className="text-sm font-medium text-text-primary">{String(value ?? "—")}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Prediction History ({predictions.length})</CardTitle>
        </CardHeader>
        {predictions.length === 0 ? (
          <p className="text-sm text-text-muted">No predictions have been made for this customer yet.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-border-subtle">
            {predictions.map((p) => (
              <li key={p.id} className="py-3">
                <button
                  type="button"
                  onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                  className="flex w-full items-center justify-between gap-3 text-left"
                >
                  <span className="flex items-center gap-3">
                    <RiskBadge level={p.risk_level} />
                    <span className="text-sm text-text-primary">{formatPercent(p.churn_probability)}</span>
                    <Badge tone="neutral">{p.prediction_type}</Badge>
                  </span>
                  <span className="text-xs text-text-muted">{formatDateTime(p.created_at)}</span>
                </button>
                {expanded === p.id && p.explanation && (
                  <div className="mt-3 rounded-control bg-bg-elevated p-3">
                    <ShapForcePlot explanation={p.explanation} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
