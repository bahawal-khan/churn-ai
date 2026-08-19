import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonStyles";

export interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

/** `docs/FRONTEND_SPEC.md` §19: "explains what's missing and gives a clear
 * next action" — every data-bearing view uses this instead of blank space. */
export function EmptyState({ title, description, actionLabel, actionHref, onAction, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-card border border-dashed border-border-subtle p-10 text-center">
      {icon && <div className="text-3xl text-text-muted">{icon}</div>}
      <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      <p className="max-w-sm text-sm text-text-muted">{description}</p>
      {actionLabel && actionHref && (
        <Link href={actionHref} className={buttonClasses("primary", "sm", "mt-2")}>
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionHref && (
        <Button size="sm" className="mt-2" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
