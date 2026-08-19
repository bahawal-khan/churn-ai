"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { Icon } from "@/components/icons";
import { useToast } from "@/components/ui/Toast";
import { authApi, type UserProfile } from "@/lib/api/auth";
import { trainingApi } from "@/lib/api/training";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { formatDateTime, titleCase } from "@/lib/utils";

/** `docs/FRONTEND_SPEC.md` §4: global search, theme toggle, notifications
 * (recent training jobs — the closest real, non-mocked activity feed the
 * backend exposes; there is no dedicated notifications/audit-log read
 * endpoint yet), user menu. */
export function Topbar({ user, onOpenNav }: { user: UserProfile; onOpenNav: () => void }) {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const { showToast } = useToast();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

  const { data: recentJobs } = useSWR("topbar-recent-jobs", () => trainingApi.list(1, 5), {
    refreshInterval: 30000,
  });

  async function handleLogout() {
    try {
      await authApi.logout();
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  function handleSearchSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const query = new FormData(e.currentTarget).get("q");
    if (typeof query === "string" && query.trim()) {
      router.push(`/customers?search=${encodeURIComponent(query.trim())}`);
    }
  }

  const recentActivity = recentJobs?.data ?? [];

  return (
    <header className="flex h-16 items-center gap-3 border-b border-border-subtle bg-bg-surface px-4">
      <button
        type="button"
        onClick={onOpenNav}
        aria-label="Open navigation menu"
        className="flex h-11 w-11 items-center justify-center rounded-control hover:bg-bg-elevated md:hidden"
      >
        <Icon name="menu" />
      </button>

      <form onSubmit={handleSearchSubmit} className="hidden max-w-sm flex-1 items-center gap-2 md:flex">
        <label htmlFor="topbar-search" className="sr-only">
          Search customers
        </label>
        <div className="flex h-10 flex-1 items-center gap-2 rounded-control border border-border-subtle bg-bg-app px-3">
          <Icon name="search" className="text-text-muted" size={16} />
          <input
            id="topbar-search"
            name="q"
            type="search"
            placeholder="Search customers…"
            className="w-full bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
          />
        </div>
      </form>

      <div className="ml-auto flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          className="flex h-11 w-11 items-center justify-center rounded-control hover:bg-bg-elevated"
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} />
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => setNotifOpen((v) => !v)}
            aria-label="Notifications"
            aria-expanded={notifOpen}
            className="relative flex h-11 w-11 items-center justify-center rounded-control hover:bg-bg-elevated"
          >
            <Icon name="bell" />
            {recentActivity.length > 0 && (
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-accent-primary" aria-hidden="true" />
            )}
          </button>
          {notifOpen && (
            <div className="absolute right-0 top-12 z-30 w-72 rounded-card border border-border-subtle bg-bg-surface p-2 shadow-elevated">
              <p className="px-2 py-1 text-xs font-semibold uppercase text-text-muted">Recent training activity</p>
              {recentActivity.length === 0 && (
                <p className="px-2 py-3 text-sm text-text-muted">No recent activity yet.</p>
              )}
              {recentActivity.map((job) => (
                <Link
                  key={job.id}
                  href="/train"
                  onClick={() => setNotifOpen(false)}
                  className="block rounded-control px-2 py-2 text-sm hover:bg-bg-elevated"
                >
                  <p className="text-text-primary">
                    Training job #{job.id} — {titleCase(job.status)}
                  </p>
                  <p className="text-xs text-text-muted">{formatDateTime(job.created_at)}</p>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => setUserMenuOpen((v) => !v)}
            aria-expanded={userMenuOpen}
            className="flex h-11 items-center gap-2 rounded-control px-2 hover:bg-bg-elevated"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-primary-soft text-sm font-semibold text-accent-primary">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <span className="hidden text-sm font-medium text-text-primary sm:inline">{user.full_name}</span>
            <Icon name="chevronDown" size={16} className="text-text-muted" />
          </button>
          {userMenuOpen && (
            <div className="absolute right-0 top-12 z-30 w-56 rounded-card border border-border-subtle bg-bg-surface p-2 shadow-elevated">
              <div className="px-2 py-1.5">
                <p className="truncate text-sm font-medium text-text-primary">{user.full_name}</p>
                <p className="truncate text-xs text-text-muted">{user.email}</p>
              </div>
              <Link
                href="/settings"
                onClick={() => setUserMenuOpen(false)}
                className="block rounded-control px-2 py-2 text-sm text-text-primary hover:bg-bg-elevated"
              >
                Settings
              </Link>
              <button
                type="button"
                onClick={() => {
                  setUserMenuOpen(false);
                  handleLogout();
                  showToast("Logged out.", "info");
                }}
                className="flex w-full items-center gap-2 rounded-control px-2 py-2 text-left text-sm text-danger hover:bg-danger-soft"
              >
                <Icon name="logout" size={16} />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
