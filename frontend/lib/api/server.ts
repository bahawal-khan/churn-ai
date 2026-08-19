import { cookies } from "next/headers";

import type { UserProfile } from "./auth";

const INTERNAL_API_BASE_URL = process.env.INTERNAL_API_BASE_URL || "http://127.0.0.1:5000";

/** Server-side session check for layout-level route protection
 * (`docs/FRONTEND_SPEC.md` §6: "every route under the authenticated app
 * shell checks session validity server-side"). Fetches the backend
 * directly (not through the Next.js dev proxy, which only intercepts
 * browser-originated requests) forwarding the session cookie from the
 * incoming request. Returns `null` on any non-200 (no session, expired,
 * network hiccup) — callers redirect to `/login`. */
export async function getServerSession(): Promise<UserProfile | null> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  try {
    const response = await fetch(`${INTERNAL_API_BASE_URL}/api/auth/session`, {
      headers: { Cookie: cookieHeader },
      cache: "no-store",
    });
    if (!response.ok) return null;
    const body = await response.json();
    return body.data as UserProfile;
  } catch {
    return null;
  }
}
