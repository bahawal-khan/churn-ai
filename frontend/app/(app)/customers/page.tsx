"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import useSWR from "swr";

import { DataTable } from "@/components/common/DataTable";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { customersApi } from "@/lib/api/customers";
import type { RiskLevel } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

function CustomersPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [riskLevel, setRiskLevel] = useState<string>("");
  const [page, setPage] = useState(1);

  const customers = useSWR(
    ["customers", search, riskLevel, page],
    () => customersApi.list({ page, pageSize: 20, search: search || undefined, riskLevel: (riskLevel || undefined) as RiskLevel | undefined })
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Customers</h1>
        <p className="text-sm text-text-muted">All customers stored across your uploads and predictions.</p>
      </div>

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <Input
              placeholder="Search by customer ID…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="sm:w-48">
            <Select
              placeholder="All risk levels"
              value={riskLevel}
              onChange={(e) => {
                setRiskLevel(e.target.value);
                setPage(1);
              }}
              options={[
                { value: "low", label: "Low Risk" },
                { value: "medium", label: "Medium Risk" },
                { value: "high", label: "High Risk" },
              ]}
            />
          </div>
        </div>
      </Card>

      <Card>
        {customers.error ? (
          <ErrorState error={customers.error} onRetry={() => customers.mutate()} />
        ) : !customers.data ? (
          <TableSkeleton rows={8} columns={5} />
        ) : customers.data.data.length === 0 ? (
          <EmptyState
            title="No customers yet"
            description="Upload a dataset or run a batch prediction to see customers here."
            actionLabel="Upload data"
            actionHref="/upload"
          />
        ) : (
          <DataTable
            rows={customers.data.data}
            getRowId={(c) => c.id}
            onRowClick={(c) => router.push(`/customers/${c.id}`)}
            pagination={{
              page: customers.data.pagination.page,
              totalPages: customers.data.pagination.total_pages,
              onPageChange: setPage,
            }}
            columns={[
              { key: "id", header: "Customer", render: (c) => c.external_customer_id ?? `#${c.id}` },
              { key: "risk", header: "Risk Level", render: (c) => <RiskBadge level={c.latest_risk_level} /> },
              {
                key: "contract",
                header: "Contract",
                render: (c) => String(c.feature_data["Contract"] ?? "—"),
              },
              {
                key: "tenure",
                header: "Tenure (months)",
                render: (c) => String(c.feature_data["Tenure Months"] ?? "—"),
              },
              { key: "created_at", header: "Added", render: (c) => formatDate(c.created_at), sortValue: (c) => c.created_at },
            ]}
          />
        )}
      </Card>
    </div>
  );
}

export default function CustomersPage() {
  return (
    <Suspense fallback={null}>
      <CustomersPageInner />
    </Suspense>
  );
}
