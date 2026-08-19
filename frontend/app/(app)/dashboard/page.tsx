"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import useSWR from "swr";

import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { useSession } from "@/lib/auth/useSession";

import { ActiveModelCard } from "@/components/dashboard/ActiveModelCard";
import { ChurnTrendChart } from "@/components/dashboard/ChurnTrendChart";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { RiskDonutChart } from "@/components/dashboard/RiskDonutChart";
import { SegmentBreakdownChart } from "@/components/dashboard/SegmentBreakdownChart";
import { TopDriversBarList } from "@/components/dashboard/TopDriversBarList";
import { RiskBadge } from "@/components/common/RiskBadge";
import { DataTable } from "@/components/common/DataTable";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { ChartSkeleton, KpiCardSkeleton, TableSkeleton } from "@/components/ui/Skeleton";
import { analyticsApi } from "@/lib/api/analytics";
import { datasetsApi } from "@/lib/api/datasets";
import { getActiveModelDetail } from "@/lib/api/models";
import { predictionsApi } from "@/lib/api/predictions";
import { formatDate, formatNumber, formatPercent } from "@/lib/utils";
import { glossary } from "@/lib/glossary";

function DashboardPageInner() {
  const dashboard = useSWR("dashboard-summary", () => analyticsApi.dashboard());
  const riskDist = useSWR("dashboard-risk-distribution", () => analyticsApi.riskDistribution());
  const trend = useSWR("dashboard-churn-trend", () => analyticsApi.churnTrend());
  const drivers = useSWR("dashboard-top-drivers", () => analyticsApi.topDrivers());
  const segments = useSWR("dashboard-segments", () => analyticsApi.segments());
  const recentPredictions = useSWR("dashboard-recent-predictions", () => predictionsApi.history(1, 5));
  const recentDatasets = useSWR("dashboard-recent-datasets", () => datasetsApi.list(1, 5));
  const activeModel = useSWR("dashboard-active-model", () => getActiveModelDetail());

  const { user, refresh } = useSession();
  const searchParams = useSearchParams();
  const [tourDismissed, setTourDismissed] = useState(false);
  const shouldShowTour =
    !tourDismissed && Boolean(user) && (user?.onboarding_completed_at === null || searchParams.get("tour") === "replay");

  if (dashboard.error) {
    return <ErrorState error={dashboard.error} onRetry={() => dashboard.mutate()} />;
  }

  const summary = dashboard.data;
  const hasAnyScoredCustomers = (summary?.scored_customers ?? 0) > 0;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-sm text-text-muted">An overview of your churn risk, predictions, and active model.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {!summary ? (
          Array.from({ length: 4 }).map((_, i) => <KpiCardSkeleton key={i} />)
        ) : (
          <>
            <KpiCard label="Total Customers" value={formatNumber(summary.total_customers)} />
            <KpiCard
              label="At Risk"
              value={formatNumber(summary.at_risk_customers)}
              tone="warning"
              tooltip={glossary.riskLevel.definition}
            />
            <KpiCard
              label="Predicted Churn Rate"
              value={formatPercent(summary.predicted_churn_rate)}
              tone="accent"
              tooltip={glossary.churnProbability.definition}
            />
            <KpiCard label="High Risk Customers" value={formatNumber(summary.high_risk_customers)} tone="danger" />
          </>
        )}
      </div>

      {!hasAnyScoredCustomers && summary && (
        <EmptyState
          title="No predictions yet"
          description="Run your first prediction to see churn risk, trends, and drivers here."
          actionLabel="Run a prediction"
          actionHref="/predict"
        />
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Churn Trend</CardTitle>
          </CardHeader>
          {trend.error ? (
            <ErrorState error={trend.error} onRetry={() => trend.mutate()} />
          ) : !trend.data ? (
            <ChartSkeleton className="h-64" />
          ) : trend.data.points.length === 0 ? (
            <EmptyState title="No trend data yet" description="Predictions will appear here as they're made." />
          ) : (
            <ChurnTrendChart points={trend.data.points} />
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Churn Risk Distribution</CardTitle>
          </CardHeader>
          {riskDist.error ? (
            <ErrorState error={riskDist.error} onRetry={() => riskDist.mutate()} />
          ) : !riskDist.data ? (
            <ChartSkeleton className="h-52" />
          ) : riskDist.data.scored_customers === 0 ? (
            <EmptyState title="No scored customers yet" description="Predictions determine risk distribution." />
          ) : (
            <RiskDonutChart counts={riskDist.data.counts} total={riskDist.data.scored_customers} />
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Predictions</CardTitle>
          </CardHeader>
          {recentPredictions.error ? (
            <ErrorState error={recentPredictions.error} onRetry={() => recentPredictions.mutate()} />
          ) : !recentPredictions.data ? (
            <TableSkeleton rows={5} columns={4} />
          ) : (
            <DataTable
              rows={recentPredictions.data.data}
              getRowId={(r) => r.id}
              emptyMessage="No predictions yet — run your first prediction."
              columns={[
                {
                  key: "id",
                  header: "Prediction",
                  render: (r) => (
                    <Link href={r.customer_id ? `/customers/${r.customer_id}` : "/predict"} className="text-accent-primary hover:underline">
                      #{r.id}
                    </Link>
                  ),
                },
                { key: "risk", header: "Risk", render: (r) => <RiskBadge level={r.risk_level} /> },
                {
                  key: "probability",
                  header: "Probability",
                  render: (r) => formatPercent(r.churn_probability),
                  sortValue: (r) => r.churn_probability,
                },
                {
                  key: "created_at",
                  header: "Date",
                  render: (r) => formatDate(r.created_at),
                  sortValue: (r) => r.created_at,
                },
              ]}
            />
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Model</CardTitle>
          </CardHeader>
          {activeModel.error ? (
            <ErrorState error={activeModel.error} onRetry={() => activeModel.mutate()} />
          ) : !activeModel.data && !activeModel.isLoading ? (
            <EmptyState
              title="No active model"
              description="No model is currently available to serve predictions."
              actionLabel="Manage models"
              actionHref="/models"
            />
          ) : !activeModel.data ? (
            <div className="flex flex-col gap-2">
              <ChartSkeleton className="h-24" />
            </div>
          ) : (
            <ActiveModelCard model={activeModel.data} />
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top Churn Drivers</CardTitle>
          </CardHeader>
          {drivers.error ? (
            <ErrorState error={drivers.error} onRetry={() => drivers.mutate()} />
          ) : !drivers.data ? (
            <ChartSkeleton className="h-40" />
          ) : !drivers.data.available || !drivers.data.feature_importance?.length ? (
            <EmptyState title="No driver data yet" description="Available once the active model has SHAP data." />
          ) : (
            <TopDriversBarList features={drivers.data.feature_importance.slice(0, 8)} />
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk by Contract Type</CardTitle>
          </CardHeader>
          {segments.error ? (
            <ErrorState error={segments.error} onRetry={() => segments.mutate()} />
          ) : !segments.data ? (
            <ChartSkeleton className="h-64" />
          ) : !segments.data.segments["Contract"] || Object.keys(segments.data.segments["Contract"]).length === 0 ? (
            <EmptyState title="No segment data yet" description="Available once customers have been scored." />
          ) : (
            <SegmentBreakdownChart breakdown={segments.data.segments["Contract"]} />
          )}
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Uploads</CardTitle>
        </CardHeader>
        {recentDatasets.error ? (
          <ErrorState error={recentDatasets.error} onRetry={() => recentDatasets.mutate()} />
        ) : !recentDatasets.data ? (
          <TableSkeleton rows={3} columns={3} />
        ) : (
          <DataTable
            rows={recentDatasets.data.data}
            getRowId={(d) => d.id}
            emptyMessage="No uploads yet."
            columns={[
              { key: "filename", header: "File", render: (d) => d.original_filename },
              { key: "rows", header: "Rows", render: (d) => formatNumber(d.row_count) },
              { key: "created_at", header: "Uploaded", render: (d) => formatDate(d.created_at) },
            ]}
          />
        )}
      </Card>

      {shouldShowTour && (
        <OnboardingTour
          onDone={() => {
            setTourDismissed(true);
            refresh();
          }}
        />
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardPageInner />
    </Suspense>
  );
}
