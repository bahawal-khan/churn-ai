import { cn } from "@/lib/utils";

export interface StepperStep {
  key: string;
  label: string;
}

export type StepStatus = "done" | "active" | "failed" | "pending";

export function ProgressStepper({
  steps,
  statusFor,
}: {
  steps: StepperStep[];
  statusFor: (key: string, index: number) => StepStatus;
}) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-3" aria-label="Progress">
      {steps.map((step, index) => {
        const status = statusFor(step.key, index);
        return (
          <li key={step.key} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold",
                status === "done" && "border-risk-low bg-risk-low-soft text-risk-low",
                status === "active" && "border-accent-primary bg-accent-primary-soft text-accent-primary",
                status === "failed" && "border-danger bg-danger-soft text-danger",
                status === "pending" && "border-border-subtle text-text-muted"
              )}
              aria-current={status === "active" ? "step" : undefined}
            >
              {status === "done" ? "✓" : index + 1}
            </span>
            <span
              className={cn(
                "text-sm",
                status === "active" ? "font-semibold text-text-primary" : "text-text-muted"
              )}
            >
              {step.label}
            </span>
            {index < steps.length - 1 && <span className="mx-1 h-px w-6 bg-border-subtle" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}
