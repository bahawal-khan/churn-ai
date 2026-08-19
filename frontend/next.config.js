/** @type {import('next').NextConfig} */
// Phase 10 dev-only same-origin proxy: the backend (`docs/BACKEND_SPEC.md`
// §1) has no CORS configured yet (deliberately deferred to Phase 11). Rather
// than adding CORS now, every `/api/*` call from the browser stays relative
// and Next.js forwards it server-side to the real Flask backend, so
// `Set-Cookie` arrives same-origin and session cookies just work with zero
// backend changes. `INTERNAL_API_BASE_URL` is server-only (no `NEXT_PUBLIC_`
// prefix) since it's never read in the browser.
const INTERNAL_API_BASE_URL = process.env.INTERNAL_API_BASE_URL || "http://127.0.0.1:5000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${INTERNAL_API_BASE_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
