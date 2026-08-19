import { redirect } from "next/navigation";

import { AppShell } from "@/components/layout/AppShell";
import { getServerSession } from "@/lib/api/server";

/** `docs/FRONTEND_SPEC.md` §6: middleware.ts already blocks unauthenticated
 * requests to every route under this group; this session fetch is defense
 * in depth (e.g. a session that expired in the moment between middleware
 * and render) and supplies the user object `AppShell`'s Topbar needs. */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getServerSession();
  if (!user) redirect("/login");

  return <AppShell user={user}>{children}</AppShell>;
}
