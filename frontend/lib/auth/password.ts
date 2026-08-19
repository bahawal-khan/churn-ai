/** Mirrors `backend/validation/schemas.py::_validate_password_policy`
 * exactly (`docs/FRONTEND_SPEC.md` §6: "client-side check mirrors the
 * server-side source of truth, never diverges from it"). */
export interface PasswordCheck {
  label: string;
  passed: boolean;
}

export function checkPasswordPolicy(password: string): PasswordCheck[] {
  return [
    { label: "At least 8 characters", passed: password.length >= 8 },
    { label: "One uppercase letter", passed: /[A-Z]/.test(password) },
    { label: "One lowercase letter", passed: /[a-z]/.test(password) },
    { label: "One number", passed: /[0-9]/.test(password) },
    { label: "One special character", passed: /[^A-Za-z0-9]/.test(password) },
  ];
}

export type PasswordStrength = "weak" | "fair" | "strong";

export function passwordStrength(password: string): PasswordStrength {
  if (!password) return "weak";
  const passedCount = checkPasswordPolicy(password).filter((c) => c.passed).length;
  if (passedCount >= 5) return "strong";
  if (passedCount >= 3) return "fair";
  return "weak";
}

export function isPasswordValid(password: string): boolean {
  return checkPasswordPolicy(password).every((c) => c.passed);
}
