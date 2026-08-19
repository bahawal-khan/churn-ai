import { Icon, type IconName } from "@/components/icons";
import { cn } from "@/lib/utils";

export type IconTileColor = "purple" | "blue" | "cyan" | "pink" | "orange" | "teal";

const GRADIENTS: Record<IconTileColor, string> = {
  purple: "from-glow-purple to-glow-blue",
  blue: "from-glow-blue to-glow-cyan",
  cyan: "from-glow-cyan to-glow-teal",
  pink: "from-glow-pink to-glow-orange",
  orange: "from-glow-orange to-glow-pink",
  teal: "from-glow-teal to-glow-blue",
};

const SHADOWS: Record<IconTileColor, string> = {
  purple: "shadow-[0_8px_24px_-8px_var(--glow-purple)]",
  blue: "shadow-[0_8px_24px_-8px_var(--glow-blue)]",
  cyan: "shadow-[0_8px_24px_-8px_var(--glow-cyan)]",
  pink: "shadow-[0_8px_24px_-8px_var(--glow-pink)]",
  orange: "shadow-[0_8px_24px_-8px_var(--glow-orange)]",
  teal: "shadow-[0_8px_24px_-8px_var(--glow-teal)]",
};

/** Colored gradient icon tile used across About/Features (`Design.md`
 * reference image's feature icons). Purely decorative styling — the icons
 * themselves come from the shared `Icon` set. */
export function IconTile({
  icon,
  color,
  size = "md",
  className,
}: {
  icon: IconName;
  color: IconTileColor;
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-2xl bg-gradient-to-br text-white",
        size === "md" ? "h-12 w-12" : "h-10 w-10",
        GRADIENTS[color],
        SHADOWS[color],
        className
      )}
    >
      <Icon name={icon} size={size === "md" ? 22 : 18} />
    </div>
  );
}
