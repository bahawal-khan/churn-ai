"use client";

import Link from "next/link";
import { useState } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { authApi } from "@/lib/api/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      // Always shows the same success state regardless of whether the email
      // is registered (`docs/API.md`: enumeration-safe, always 200).
      await authApi.forgotPassword(email);
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle="Enter your email and we'll send you a reset link."
      footer={
        <Link href="/login" className="font-medium text-accent-primary hover:underline">
          Back to login
        </Link>
      }
    >
      {submitted ? (
        <p className="rounded-control bg-accent-primary-soft p-3 text-sm text-text-primary">
          If an account exists for that email, we&apos;ve sent a password reset link.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Button type="submit" loading={submitting}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
