import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SWRConfig } from "swr";

import SignupPage from "./page";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

// Same fresh-SWR-cache-per-test rationale as `app/login/page.test.tsx` —
// `useRedirectIfAuthenticated` reads the shared "/api/auth/session" cache key.
function renderSignupPage() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <SignupPage />
    </SWRConfig>
  );
}

const push = jest.fn();
const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@/lib/api/auth", () => ({
  authApi: { signup: jest.fn(), session: jest.fn() },
}));

const MOCK_USER = {
  id: 1,
  email: "new.user@example.com",
  full_name: "New User",
  organization_id: 1,
  organization_name: "New User's Org",
  theme_preference: "dark" as const,
  onboarding_completed_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
  (authApi.session as jest.Mock).mockRejectedValue(
    new ApiError({ code: "SESSION_EXPIRED", message: "Not logged in.", details: {} }, 401, null)
  );
});

describe("SignupPage — flow", () => {
  it(
    "creates an authenticated session and redirects to /dashboard on success",
    async () => {
      const user = userEvent.setup();
      (authApi.signup as jest.Mock).mockResolvedValue(MOCK_USER);

      renderSignupPage();

      await user.type(await screen.findByLabelText("Full name"), "New User");
      await user.type(screen.getByLabelText("Email"), "new.user@example.com");
      // Typing into Password re-renders `PasswordStrengthMeter` on every
      // keystroke (unlike the 2-field login form), which is measurably
      // slower than Jest's 5000ms default on this machine — a longer
      // per-test timeout, not a test bug.
      await user.type(screen.getByLabelText("Password"), "StrongPass1!");
      await user.type(screen.getByLabelText("Confirm password"), "StrongPass1!");
      await user.click(screen.getByRole("button", { name: "Create account" }));

      await waitFor(() =>
        expect(authApi.signup).toHaveBeenCalledWith({
          full_name: "New User",
          email: "new.user@example.com",
          password: "StrongPass1!",
          confirm_password: "StrongPass1!",
        })
      );
      await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    },
    15000
  );

  it(
    "shows the EMAIL_ALREADY_EXISTS message inline and does not redirect",
    async () => {
      const user = userEvent.setup();
      (authApi.signup as jest.Mock).mockRejectedValue(
        new ApiError(
          { code: "EMAIL_ALREADY_EXISTS", message: "An account with this email already exists.", details: {} },
          409,
          null
        )
      );

      renderSignupPage();

      await user.type(await screen.findByLabelText("Full name"), "New User");
      await user.type(screen.getByLabelText("Email"), "taken@example.com");
      await user.type(screen.getByLabelText("Password"), "StrongPass1!");
      await user.type(screen.getByLabelText("Confirm password"), "StrongPass1!");
      await user.click(screen.getByRole("button", { name: "Create account" }));

      expect(await screen.findByText("An account with this email already exists.")).toBeInTheDocument();
      expect(push).not.toHaveBeenCalled();
    },
    15000
  );

  it("blocks submission client-side on a password/confirm-password mismatch, without calling the API", async () => {
    const user = userEvent.setup();
    renderSignupPage();

    await user.type(await screen.findByLabelText("Full name"), "New User");
    await user.type(screen.getByLabelText("Email"), "new.user@example.com");
    await user.type(screen.getByLabelText("Password"), "StrongPass1!");
    await user.type(screen.getByLabelText("Confirm password"), "Different1!");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(/must match/i)).toBeInTheDocument();
    expect(authApi.signup).not.toHaveBeenCalled();
  });
});
