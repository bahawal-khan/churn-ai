"use client";

import Link from "next/link";

import { Icon } from "@/components/icons";
import { buttonClasses } from "@/components/ui/buttonStyles";
import { Skeleton } from "@/components/ui/Skeleton";
import { useSession } from "@/lib/auth/useSession";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { cn } from "@/lib/utils";

/** `docs/FRONTEND_SPEC.md` §4: public navbar. Swaps Login/Sign Up for a
 * single "Go to Dashboard" CTA when a valid session already exists, rather
 * than showing auth CTAs to an already-authenticated visitor. Reads the same
 * deduped `useSession` SWR cache (`/api/auth/session`) the authenticated app
 * uses, rather than a separate fetch, and waits for it to resolve before
 * choosing a CTA so the logged-out buttons never flash for an
 * already-authenticated visitor. */
export function MarketingNavbar() {
  const { theme, setTheme } = useTheme();
  const { user, isLoading } = useSession();

  return (
    <header className="sticky top-0 z-30 border-b border-marketing-border bg-marketing-surface-solid/80 backdrop-blur-lg supports-[backdrop-filter]:bg-marketing-surface-solid/60">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-6">
        <Link href="/" className="flex items-center gap-2.5 font-bold text-text-primary">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-glow-purple to-glow-blue text-sm text-white shadow-[0_4px_16px_-4px_var(--glow-purple)]">
            C
          </div>
          ChurnAI
        </Link>
        <nav className="ml-4 hidden gap-6 text-sm text-text-muted md:flex">
          <Link href="/#features" className="transition-colors hover:text-text-primary">
            Features
          </Link>
          <Link href="/help" className="transition-colors hover:text-text-primary">
            FAQ
          </Link>
          <Link href="/about" className="transition-colors hover:text-text-primary">
            About
          </Link>
          <Link href="/contact" className="transition-colors hover:text-text-primary">
            Contact
          </Link>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="flex h-10 w-10 items-center justify-center rounded-control text-text-muted transition-colors hover:bg-bg-elevated hover:text-text-primary"
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          {isLoading ? (
            <Skeleton className="h-8 w-32" />
          ) : user ? (
            <Link
              href="/dashboard"
              className={cn(buttonClasses("primary", "sm"), "bg-gradient-to-r from-glow-purple to-glow-blue hover:opacity-90")}
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className={cn(buttonClasses("ghost", "sm"))}>
                Login
              </Link>
              <Link
                href="/signup"
                className={cn(buttonClasses("primary", "sm"), "bg-gradient-to-r from-glow-purple to-glow-blue hover:opacity-90")}
              >
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
