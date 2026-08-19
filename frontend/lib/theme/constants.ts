/** Shared between the server (`app/layout.tsx`, reading the cookie via
 * `next/headers`) and the client (`ThemeProvider`, reading/writing
 * `document.cookie`) so both sides agree on the same cookie name. */
export const THEME_COOKIE = "churnai_theme";

export type Theme = "light" | "dark";

/** Pure resolution rule shared by server and client so both compute the
 * same fallback chain from the same explicit inputs: signed-in user's
 * `theme_preference` -> theme cookie (manual override, `docs/FRONTEND_SPEC.md`
 * §3) -> the DB's own default (`users.theme_preference DEFAULT 'dark'`,
 * `docs/DATABASE_SPEC.md` §2.1). Deliberately does NOT consult
 * `prefers-color-scheme` here — that's only knowable client-side and is
 * applied, pre-paint, by the inline script in `app/layout.tsx` for a
 * brand-new anonymous visitor with no cookie yet. */
export function resolveTheme(sessionTheme: Theme | null | undefined, cookieTheme: Theme | null | undefined): Theme {
  return sessionTheme ?? cookieTheme ?? "dark";
}
