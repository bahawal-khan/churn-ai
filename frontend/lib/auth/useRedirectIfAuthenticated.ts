"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "./useSession";

/** `docs/FRONTEND_SPEC.md` §6: "/login and /signup call GET /api/auth/session
 * on mount; a valid session immediately redirects to /dashboard without
 * flashing the auth form." Honors `?next=` set by `middleware.ts`'s
 * protected-route redirect. */
export function useRedirectIfAuthenticated() {
  const { user, isLoading } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (user) {
      const next = searchParams.get("next");
      router.replace(next && next.startsWith("/") ? next : "/dashboard");
    }
  }, [user, router, searchParams]);

  return { checking: isLoading, alreadyAuthenticated: Boolean(user) };
}
