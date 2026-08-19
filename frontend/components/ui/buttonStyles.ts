import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-accent-primary text-white hover:bg-accent-primary-hover",
  secondary:
    "bg-bg-elevated text-text-primary border border-border-subtle hover:border-border-strong",
  ghost: "bg-transparent text-text-primary hover:bg-bg-elevated",
  danger: "bg-danger text-white hover:opacity-90",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-base gap-2",
};

/** Plain (non-`"use client"`) module so Server Components — e.g. the
 * marketing pages — can call `buttonClasses` directly (a `<Link>` styled
 * like a `Button`) without crossing the client/server boundary. `Button.tsx`
 * itself re-exports this for backwards-compatible imports. */
export function buttonClasses(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "md",
  className?: string
): string {
  return cn(
    "inline-flex items-center justify-center rounded-control font-medium transition-colors",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    "min-h-[44px] sm:min-h-0",
    variantClasses[variant],
    sizeClasses[size],
    className
  );
}
