"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { PasswordStrengthMeter } from "@/components/auth/PasswordStrengthMeter";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { isPasswordValid } from "@/lib/auth/password";
import { useRedirectIfAuthenticated } from "@/lib/auth/useRedirectIfAuthenticated";

export default function SignupPage() {
  const { checking, alreadyAuthenticated } = useRedirectIfAuthenticated();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [touched, setTouched] = useState(false);

  const confirmMismatch = touched && confirmPassword.length > 0 && password !== confirmPassword;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    setEmailError(null);
    setFormError(null);

    if (!isPasswordValid(password)) {
      setFormError("Password does not meet all requirements below.");
      return;
    }
    if (password !== confirmPassword) {
      setFormError("Password and confirm password must match.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.signup({
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
      });
      // Don't pre-populate the shared "/api/auth/session" SWR cache here: this
      // component also reads it via useRedirectIfAuthenticated, so doing so
      // flips `alreadyAuthenticated` and unmounts this page (blank screen)
      // while router.push's navigation to /dashboard is still in flight. The
      // destination route fetches the session itself server-side.
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.code === "EMAIL_ALREADY_EXISTS") {
        setEmailError(err.message);
      } else {
        setFormError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (checking || alreadyAuthenticated) return null;

  return (
    <AuthCard
      title="Create your ChurnAI account"
      subtitle="Set up your workspace to start predicting churn."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-accent-primary hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <Input
          label="Full name"
          autoComplete="name"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          required
          error={emailError ?? undefined}
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setEmailError(null);
          }}
        />
        <div>
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <PasswordStrengthMeter password={password} />
        </div>
        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          error={confirmMismatch ? "Passwords do not match." : undefined}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          onBlur={() => setTouched(true)}
        />
        {formError && (
          <p role="alert" className="rounded-control bg-danger-soft p-2.5 text-sm text-danger">
            {formError}
          </p>
        )}
        <Button type="submit" loading={submitting} className="mt-1">
          Create account
        </Button>
      </form>
    </AuthCard>
  );
}
