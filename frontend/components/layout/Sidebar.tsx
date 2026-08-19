"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "@/components/icons";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: IconName;
}

/** `docs/FRONTEND_SPEC.md` §4: sidebar section order. */
const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/upload", label: "Upload Data", icon: "upload" },
  { href: "/train", label: "Train Model", icon: "train" },
  { href: "/predict", label: "Predictions", icon: "predict" },
  { href: "/customers", label: "Customers", icon: "customers" },
  { href: "/analytics", label: "Analytics", icon: "analytics" },
  { href: "/models", label: "Model Management", icon: "models" },
  { href: "/reports", label: "Reports", icon: "reports" },
  { href: "/settings", label: "Settings", icon: "settings" },
  { href: "/help", label: "Help & Support", icon: "help" },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1 p-3">
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex min-h-[44px] items-center gap-3 rounded-control px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent-primary text-white"
                : "text-text-muted hover:bg-bg-elevated hover:text-text-primary"
            )}
          >
            <Icon name={item.icon} />
            <span className="truncate">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** Desktop/tablet sidebar. Collapses to an icon rail below `lg`
 * (`docs/FRONTEND_SPEC.md` §21); the separate mobile drawer variant is
 * `MobileNavDrawer`, opened from `Topbar`. */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-screen shrink-0 border-r border-border-subtle bg-bg-surface md:flex md:w-16 lg:w-60 md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-border-subtle px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent-primary text-sm font-bold text-white">
          C
        </div>
        <span className="hidden text-base font-bold text-text-primary lg:inline">ChurnAI</span>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto [&_span.truncate]:hidden lg:[&_span.truncate]:inline">
        <NavLinks pathname={pathname} />
      </div>
    </aside>
  );
}

export function MobileNavDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative flex h-full w-72 flex-col bg-bg-surface shadow-elevated">
        <div className="flex h-16 items-center justify-between border-b border-border-subtle px-4">
          <span className="text-base font-bold text-text-primary">ChurnAI</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation menu"
            className="flex h-11 w-11 items-center justify-center rounded-control hover:bg-bg-elevated"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto">
          <NavLinks pathname={pathname} onNavigate={onClose} />
        </div>
      </div>
    </div>
  );
}
