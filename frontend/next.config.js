/** @type {import('next').NextConfig} */
// Dev-only same-origin proxy: the backend now has a real CORS allow-list
// (`backend/app.py`, `docs/BACKEND_SPEC.md` §9, Phase 11), but local dev
// keeps using this proxy rather than relying on it — every `/api/*` call
// from the browser stays relative and Next.js forwards it server-side to
// the real Flask backend, so `Set-Cookie` arrives same-origin with zero
// cross-origin cookie edge cases during development. Production (Vercel +
// PythonAnywhere, `docs/DEPLOYMENT.md`) calls the backend directly via
// `NEXT_PUBLIC_API_BASE_URL`, where the real CORS allow-list applies.
// `INTERNAL_API_BASE_URL` is server-only (no `NEXT_PUBLIC_` prefix) since
// it's never read in the browser.
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
