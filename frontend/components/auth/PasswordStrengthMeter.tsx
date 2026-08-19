"use client";

import { checkPasswordPolicy, passwordStrength } from "@/lib/auth/password";
import { cn } from "@/lib/utils";

const STRENGTH_COLOR: Record<string, string> = {
  weak: "bg-risk-high",
  fair: "bg-risk-medium",
  strong: "bg-risk-low",
};

export function PasswordStrengthMeter({ password }: { password: string }) {
  const checks = checkPasswordPolicy(password);
  const strength = passwordStrength(password);

  return (
    <div className="mt-1.5 flex flex-col gap-2">
      <div className="flex h-1.5 gap-1">
        {[0, 1, 2].map((segment) => (
          <div
            key={segment}
            className={cn(
              "flex-1 rounded-full bg-border-subtle",
              (strength === "weak" && segment === 0) ||
                (strength === "fair" && segment <= 1) ||
                (strength === "strong")
                ? STRENGTH_COLOR[strength]
                : undefined
            )}
          />
        ))}
      </div>
      <ul className="grid grid-cols-1 gap-x-3 gap-y-0.5 text-xs text-text-muted sm:grid-cols-2">
        {checks.map((check) => (
          <li key={check.label} className={cn("flex items-center gap-1.5", check.passed && "text-risk-low")}>
            <span aria-hidden="true">{check.passed ? "✓" : "○"}</span>
            {check.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
