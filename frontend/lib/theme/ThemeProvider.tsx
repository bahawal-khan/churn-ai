"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { authApi } from "@/lib/api/auth";
import { THEME_COOKIE, type Theme } from "./constants";

export type { Theme };

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme, opts?: { persistToServer?: boolean }) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function writeCookieTheme(theme: Theme) {
  document.cookie = `${THEME_COOKIE}=${theme}; path=/; max-age=31536000; SameSite=Lax`;
}

/** `docs/FRONTEND_SPEC.md` §3: authenticated users persist `theme_preference`
 * server-side (`PATCH /api/auth/profile`, so it follows them across
 * devices); an unauthenticated visitor uses OS `prefers-color-scheme` with a
 * manual override kept in a cookie until they sign in.
 *
 * `initialTheme` is the value `app/layout.tsx` already resolved and rendered
 * server-side (`<html data-theme={initialTheme}>`) via the same
 * `resolveTheme` rule — a plain prop threaded identically through the SSR
 * pass and the client's hydration pass, so this component's very first
 * render produces the same output in both places. It must NOT be
 * recomputed here from `document.cookie`/`window.matchMedia`: those are
 * unavailable during SSR and available during hydration, so reading them in
 * the `useState` initializer would make the hydration pass diverge from the
 * SSR pass — exactly the bug this component previously had (a genuine
 * hydration mismatch, not just a cosmetic one, since `theme` also drives the
 * Sun/Moon icon in `Topbar`/`MarketingNavbar`). */
export function ThemeProvider({
  initialTheme,
  isAuthenticated,
  children,
}: {
  initialTheme: Theme;
  isAuthenticated: boolean;
  children: React.ReactNode;
}) {
  const [theme, setThemeState] = useState<Theme>(initialTheme);

  // One-time, post-hydration reconciliation: the only case `initialTheme`
  // can legitimately differ from what's actually on screen is a brand-new
  // anonymous visitor with no cookie yet, where `app/layout.tsx`'s inline
  // script applies `prefers-color-scheme` to the DOM *before paint* (a
  // value the server could never have known). That script only touches the
  // DOM attribute, not React state, so this syncs state to match once,
  // after hydration has already committed — a normal post-mount state
  // update, not a hydration diff.
  useEffect(() => {
    const domTheme = document.documentElement.getAttribute("data-theme") as Theme | null;
    if (domTheme && domTheme !== theme) {
      setThemeState(domTheme);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setTheme = useCallback(
    (next: Theme, opts: { persistToServer?: boolean } = {}) => {
      setThemeState(next);
      document.documentElement.setAttribute("data-theme", next);
      writeCookieTheme(next);
      const shouldPersist = opts.persistToServer ?? isAuthenticated;
      if (shouldPersist) {
        authApi.updateProfile({ theme_preference: next }).catch(() => {
          // Non-fatal: the theme still applies locally even if the
          // server-side persistence call fails (e.g. transient network).
        });
      }
    },
    [isAuthenticated]
  );

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
