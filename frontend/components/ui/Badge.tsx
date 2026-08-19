import { cn } from "@/lib/utils";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "accent";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-bg-elevated text-text-muted border-border-subtle",
  success: "bg-risk-low-soft text-risk-low border-transparent",
  warning: "bg-risk-medium-soft text-risk-medium border-transparent",
  danger: "bg-risk-high-soft text-risk-high border-transparent",
  accent: "bg-accent-primary-soft text-accent-primary border-transparent",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-pill border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
