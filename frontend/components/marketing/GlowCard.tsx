import { cn } from "@/lib/utils";

/** `Design.md` "Cards": layered shading, soft shadow, gradient border that
 * lights up on hover, and a smooth lift. The gradient border is the standard
 * two-layer trick (outer padding-box gradient + inner solid surface) rather
 * than an actual `border`, since a plain border can't hold a gradient that
 * only appears on hover without a repaint flash. Public-page-only — the
 * shared `components/ui/Card` used across the authenticated app is
 * untouched. */
export function GlowCard({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "group relative rounded-2xl bg-gradient-to-br from-marketing-border to-marketing-border p-px",
        "transition-all duration-300 ease-out hover:-translate-y-1 hover:from-glow-purple hover:to-glow-cyan",
        "shadow-marketing-card hover:shadow-marketing-hover"
      )}
    >
      <div
        className={cn(
          "h-full rounded-[calc(1rem-1px)] bg-marketing-surface-solid/95 p-6 backdrop-blur-sm",
          "bg-[linear-gradient(160deg,var(--marketing-surface-solid)_0%,var(--marketing-surface)_140%)]",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}
