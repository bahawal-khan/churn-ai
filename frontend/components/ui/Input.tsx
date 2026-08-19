import { forwardRef, useId } from "react";

import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const errorId = error ? `${inputId}-error` : undefined;
    const hintId = hint ? `${inputId}-hint` : undefined;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-text-primary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={Boolean(error)}
          aria-describedby={errorId ?? hintId}
          className={cn(
            "h-10 min-h-[44px] sm:min-h-0 rounded-control border bg-bg-surface px-3 text-sm text-text-primary placeholder:text-text-muted",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus-ring",
            error ? "border-danger" : "border-border-subtle",
            className
          )}
          {...props}
        />
        {error && (
          <p id={errorId} className="text-xs text-danger">
            {error}
          </p>
        )}
        {!error && hint && (
          <p id={hintId} className="text-xs text-text-muted">
            {hint}
          </p>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";
