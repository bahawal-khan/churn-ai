import { render, screen } from "@testing-library/react";
import { SWRConfig } from "swr";

import LandingPage from "./page";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

function renderLandingPage() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <LandingPage />
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

describe("LandingPage — hero CTA", () => {
  it("shows Sign Up Free for a logged-out visitor", async () => {
    (authApi.session as jest.Mock).mockRejectedValue(
      new ApiError({ code: "SESSION_EXPIRED", message: "Not logged in.", details: {} }, 401, null)
    );

    renderLandingPage();

    expect(await screen.findByRole("link", { name: "Sign Up Free" })).toBeInTheDocument();
  });

  it("shows Go to Dashboard instead of Sign Up Free for a logged-in visitor", async () => {
    (authApi.session as jest.Mock).mockResolvedValue(MOCK_USER);

    renderLandingPage();

    expect(await screen.findByRole("link", { name: "Go to Dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign Up Free" })).not.toBeInTheDocument();
  });
});
