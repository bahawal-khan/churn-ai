"use client";

import useSWR from "swr";

import { authApi, type UserProfile } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

const SESSION_KEY = "/api/auth/session";

/** Client-side session hook (SWR-cached, deduped across every component
 * that calls it). Server Components use `lib/api/server.ts::getServerSession`
 * for the initial protected-route check; this hook is for client
 * interactivity (Topbar user menu, Settings, theme toggle, logout). */
export function useSession() {
  const { data, error, isLoading, mutate } = useSWR<UserProfile>(
    SESSION_KEY,
    () => authApi.session(),
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );

  return {
    user: data ?? null,
    isLoading,
    isUnauthenticated: error instanceof ApiError && error.status === 401,
    error,
    refresh: mutate,
  };
}

export { SESSION_KEY };
