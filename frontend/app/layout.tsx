import type { Metadata } from "next";
import { cookies } from "next/headers";

import { ToastProvider } from "@/components/ui/Toast";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { THEME_COOKIE, resolveTheme, type Theme } from "@/lib/theme/constants";
import { getServerSession } from "@/lib/api/server";

import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "ChurnAI — Predict. Understand. Retain.",
  description: "AI-powered customer churn prediction and retention intelligence platform.",
};

// Pre-paint correction for a brand-new anonymous visitor: the server has no
// way to know `prefers-color-scheme`, so it renders the DB's own default
// ("dark", `resolveTheme`'s fallback) on `<html data-theme>`. If that
// visitor's OS prefers light AND they have no theme cookie yet, this script
// flips the DOM attribute before first paint (no flash). It's a no-op for
// everyone else (signed-in users and returning visitors with a cookie),
// since the server already rendered the right value for them.
// `suppressHydrationWarning` on `<html>` (below) is what makes this
// legitimate, unavoidable divergence safe instead of a hydration error.
const NO_FLASH_SCRIPT = `
(function() {
  try {
    if (document.cookie.indexOf('${THEME_COOKIE}=') !== -1) return;
    if (document.documentElement.getAttribute('data-theme') === 'dark' &&
        !window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  } catch (e) {}
})();
`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [session, cookieStore] = await Promise.all([getServerSession(), cookies()]);
  const cookieTheme = cookieStore.get(THEME_COOKIE)?.value as Theme | undefined;
  const resolvedTheme = resolveTheme(session?.theme_preference ?? null, cookieTheme ?? null);

  return (
    <html lang="en" data-theme={resolvedTheme} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_SCRIPT }} />
      </head>
      <body>
        <ThemeProvider initialTheme={resolvedTheme} isAuthenticated={Boolean(session)}>
          <ToastProvider>{children}</ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
