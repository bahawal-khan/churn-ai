import { render, screen, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";

import { MarketingNavbar } from "./MarketingNavbar";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";

// Fresh SWR cache per test so the "/api/auth/session" entry from one test
// doesn't leak into the next (same reasoning as app/login/page.test.tsx).
function renderNavbar() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <ThemeProvider initialTheme="dark" isAuthenticated={false}>
        <MarketingNavbar />
      </ThemeProvider>
    </SWRConfig>
  );
}

jest.mock("@/lib/api/auth", () => ({
  authApi: { session: jest.fn() },
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
});

describe("MarketingNavbar — auth-aware CTA", () => {
  it("shows Login/Sign Up for a logged-out visitor", async () => {
    (authApi.session as jest.Mock).mockRejectedValue(
      new ApiError({ code: "SESSION_EXPIRED", message: "Not logged in.", details: {} }, 401, null)
    );

    renderNavbar();

    expect(await screen.findByRole("link", { name: "Sign Up" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Login" })).toBeInTheDocument();
    expect(screen.queryByText("Go to Dashboard")).not.toBeInTheDocument();
  });

  it("shows Go to Dashboard, never Sign Up, for a logged-in visitor", async () => {
    (authApi.session as jest.Mock).mockResolvedValue(MOCK_USER);

    renderNavbar();

    expect(await screen.findByRole("link", { name: "Go to Dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign Up" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Login" })).not.toBeInTheDocument();
  });

  it("renders neither CTA while the session check is in flight (no flicker)", async () => {
    let resolveSession!: (value: typeof MOCK_USER) => void;
    (authApi.session as jest.Mock).mockReturnValue(
      new Promise((resolve) => {
        resolveSession = resolve;
      })
    );

    renderNavbar();

    expect(screen.queryByRole("link", { name: "Sign Up" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Go to Dashboard" })).not.toBeInTheDocument();

    resolveSession(MOCK_USER);

    expect(await screen.findByRole("link", { name: "Go to Dashboard" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("link", { name: "Sign Up" })).not.toBeInTheDocument());
  });
});
