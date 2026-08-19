import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api/client";

export interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/** `docs/FRONTEND_SPEC.md` §19: human-readable message from the API error
 * envelope, retry action where applicable, request_id for support
 * reference. */
export function ErrorState({ error, onRetry, title = "Something went wrong" }: ErrorStateProps) {
  const message = error instanceof ApiError ? error.message : "An unexpected error occurred.";
  const requestId = error instanceof ApiError ? error.requestId : null;

  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-card border border-danger/30 bg-danger-soft p-10 text-center">
      <h3 className="text-sm font-semibold text-danger">{title}</h3>
      <p className="max-w-sm text-sm text-text-primary">{message}</p>
      {requestId && <p className="text-xs text-text-muted">Reference ID: {requestId}</p>}
      {onRetry && (
        <Button size="sm" variant="secondary" className="mt-2" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
