"use client";

import Link from "next/link";

import { buttonClasses, type ButtonSize, type ButtonVariant } from "@/components/ui/buttonStyles";
import { Skeleton } from "@/components/ui/Skeleton";
import { useSession } from "@/lib/auth/useSession";
import { cn } from "@/lib/utils";

const SKELETON_SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-8 w-32",
  md: "h-10 w-36",
  lg: "h-11 w-40",
};

/** Public-page CTA (`signup.md`): resolves to "Go to Dashboard" once a
 * session is confirmed via the same deduped `useSession` SWR cache the
 * authenticated app uses (`/api/auth/session`) — no second session system.
 * Renders a same-sized skeleton while that check is in flight so an
 * already-authenticated visitor never sees the logged-out CTA flash before
 * it flips to "Go to Dashboard". */
export function AuthAwareCta({
  loggedOutHref,
  loggedOutLabel,
  variant = "primary",
  size = "sm",
  className,
}: {
  loggedOutHref: string;
  loggedOutLabel: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
}) {
  const { user, isLoading } = useSession();

  if (isLoading) {
    return <Skeleton className={cn(SKELETON_SIZE_CLASSES[size], className)} />;
  }

  if (user) {
    return (
      <Link href="/dashboard" className={cn(buttonClasses(variant, size), className)}>
        Go to Dashboard
      </Link>
    );
  }

  return (
    <Link href={loggedOutHref} className={cn(buttonClasses(variant, size), className)}>
      {loggedOutLabel}
    </Link>
  );
}
