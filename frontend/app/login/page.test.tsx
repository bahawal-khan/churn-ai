import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SWRConfig } from "swr";

import LoginPage from "./page";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

// Each test gets a fresh SWR cache (`provider: () => new Map()`) — without
// this, `useSession`'s cached "/api/auth/session" entry from one test (the
// login page optimistically mutates it on success) would leak into the
// next test and short-circuit the already-authenticated redirect check.
function renderLoginPage() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <LoginPage />
    </SWRConfig>
  );
}

const push = jest.fn();
const replace = jest.fn();
const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, refresh }),
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@/lib/api/auth", () => ({
  authApi: { login: jest.fn(), session: jest.fn() },
}));

const MOCK_USER = {
  id: 1,
  email: "user@example.com",
  full_name: "Test User",
  organization_id: 1,
  organization_name: "Test Org",
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

describe("LoginPage — flow", () => {
  it("redirects to /dashboard after a successful login", async () => {
    const user = userEvent.setup();
    (authApi.login as jest.Mock).mockResolvedValue(MOCK_USER);

    renderLoginPage();

    await user.type(await screen.findByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "StrongPass1!");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows a generic invalid-credentials message on failure, and does not redirect", async () => {
    const user = userEvent.setup();
    (authApi.login as jest.Mock).mockRejectedValue(
      new ApiError({ code: "INVALID_CREDENTIALS", message: "Invalid email or password.", details: {} }, 401, null)
    );

    renderLoginPage();

    await user.type(await screen.findByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "WrongPass1!");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
