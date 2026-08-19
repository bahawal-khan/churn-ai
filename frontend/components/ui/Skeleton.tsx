import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-control bg-bg-elevated", className)}
      aria-hidden="true"
      {...props}
    />
  );
}

export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="flex flex-col gap-2" role="status" aria-label="Loading table data">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-3">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-8 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-end gap-2", className)} role="status" aria-label="Loading chart data">
      {[40, 65, 50, 80, 55, 70, 45].map((height, i) => (
        <Skeleton key={i} className="flex-1" style={{ height: `${height}%` }} />
      ))}
    </div>
  );
}

export function KpiCardSkeleton() {
  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface p-5" role="status" aria-label="Loading">
      <Skeleton className="mb-3 h-4 w-24" />
      <Skeleton className="h-8 w-20" />
    </div>
  );
}
