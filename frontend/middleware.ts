import { NextRequest, NextResponse } from "next/server";

const INTERNAL_API_BASE_URL = process.env.INTERNAL_API_BASE_URL || "http://127.0.0.1:5000";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/upload",
  "/train",
  "/predict",
  "/customers",
  "/analytics",
  "/models",
  "/reports",
  "/settings",
  "/help",
];

/** Server-side route protection (`docs/FRONTEND_SPEC.md` §6): every
 * authenticated-app route checks session validity before rendering and
 * redirects to `/login?next=<original path>`. Runs in middleware (rather
 * than only at the layout level) so the original pathname is available for
 * the `next=` redirect param. */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!isProtected) return NextResponse.next();

  const cookieHeader = request.headers.get("cookie") ?? "";
  try {
    const response = await fetch(`${INTERNAL_API_BASE_URL}/api/auth/session`, {
      headers: { Cookie: cookieHeader },
      cache: "no-store",
    });
    if (response.ok) return NextResponse.next();
  } catch {
    // Backend unreachable: fall through to the login redirect below rather
    // than rendering a protected page against a session we couldn't verify.
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/upload/:path*",
    "/train/:path*",
    "/predict/:path*",
    "/customers/:path*",
    "/analytics/:path*",
    "/models/:path*",
    "/reports/:path*",
    "/settings/:path*",
    "/help/:path*",
  ],
};
