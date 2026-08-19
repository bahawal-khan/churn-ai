"use client";

import { useState } from "react";

import { MobileNavDrawer, Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Footer } from "@/components/layout/Footer";
import type { UserProfile } from "@/lib/api/auth";

export function AppShell({ user, children }: { user: UserProfile; children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <MobileNavDrawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar user={user} onOpenNav={() => setMobileNavOpen(true)} />
        <main className="flex-1 p-4 sm:p-6">{children}</main>
        <Footer compact />
      </div>
    </div>
  );
}
