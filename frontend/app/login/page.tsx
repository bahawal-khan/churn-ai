"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { useRedirectIfAuthenticated } from "@/lib/auth/useRedirectIfAuthenticated";

export default function LoginPage() {
  const { checking, alreadyAuthenticated } = useRedirectIfAuthenticated();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authApi.login({ email, password });
      // See app/signup/page.tsx: don't pre-populate the shared session SWR
      // cache here — it would unmount this page (blank screen) via
      // useRedirectIfAuthenticated while router.push's navigation is pending.
      const next = searchParams.get("next");
      router.push(next && next.startsWith("/") ? next : "/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (checking || alreadyAuthenticated) return null;

  return (
    <AuthCard
      title="Log in to ChurnAI"
      subtitle="Welcome back — enter your details to continue."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="font-medium text-accent-primary hover:underline">
            Sign up
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-xs font-medium text-accent-primary hover:underline">
            Forgot password?
          </Link>
        </div>
        {error && (
          <p role="alert" className="rounded-control bg-danger-soft p-2.5 text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" loading={submitting} className="mt-1">
          Log in
        </Button>
      </form>
    </AuthCard>
  );
}
