"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { PasswordStrengthMeter } from "@/components/auth/PasswordStrengthMeter";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { isPasswordValid } from "@/lib/auth/password";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [tokenInvalid, setTokenInvalid] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setTokenInvalid(false);

    if (!isPasswordValid(password)) {
      setError("Password does not meet all requirements below.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Password and confirm password must match.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.resetPassword({ token, new_password: password, confirm_password: confirmPassword });
      setDone(true);
      setTimeout(() => router.push("/login"), 1500);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setTokenInvalid(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <p className="rounded-control bg-danger-soft p-3 text-sm text-danger">
        This reset link is missing its token. Request a new one from{" "}
        <Link href="/forgot-password" className="underline">
          forgot password
        </Link>
        .
      </p>
    );
  }

  if (tokenInvalid) {
    return (
      <p className="rounded-control bg-danger-soft p-3 text-sm text-danger">
        This password reset link is invalid or has expired. Request a new one from{" "}
        <Link href="/forgot-password" className="underline">
          forgot password
        </Link>
        .
      </p>
    );
  }

  if (done) {
    return (
      <p className="rounded-control bg-accent-primary-soft p-3 text-sm text-text-primary">
        Your password has been reset. Redirecting to login…
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div>
        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <PasswordStrengthMeter password={password} />
      </div>
      <Input
        label="Confirm new password"
        type="password"
        autoComplete="new-password"
        required
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
      />
      {error && (
        <p role="alert" className="rounded-control bg-danger-soft p-2.5 text-sm text-danger">
          {error}
        </p>
      )}
      <Button type="submit" loading={submitting}>
        Reset password
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthCard
      title="Set a new password"
      footer={
        <Link href="/login" className="font-medium text-accent-primary hover:underline">
          Back to login
        </Link>
      }
    >
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </AuthCard>
  );
}
