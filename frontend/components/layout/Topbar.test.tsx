import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Topbar } from "./Topbar";
import { ToastProvider } from "@/components/ui/Toast";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { authApi } from "@/lib/api/auth";
import { trainingApi } from "@/lib/api/training";

const push = jest.fn();
const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

jest.mock("@/lib/api/auth", () => ({
  authApi: { logout: jest.fn().mockResolvedValue({ logged_out: true }), updateProfile: jest.fn() },
}));

jest.mock("@/lib/api/training", () => ({
  trainingApi: { list: jest.fn().mockResolvedValue({ data: [], pagination: { page: 1, page_size: 5, total: 0, total_pages: 0 } }) },
}));

const MOCK_USER = {
  id: 1,
  email: "user@example.com",
  full_name: "Test User",
  organization_id: 1,
  organization_name: "Test Org",
  theme_preference: "dark" as const,
  onboarding_completed_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
};

function renderTopbar() {
  return render(
    <ThemeProvider initialTheme="dark" isAuthenticated>
      <ToastProvider>
        <Topbar user={MOCK_USER} onOpenNav={jest.fn()} />
      </ToastProvider>
    </ThemeProvider>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  (trainingApi.list as jest.Mock).mockResolvedValue({
    data: [],
    pagination: { page: 1, page_size: 5, total: 0, total_pages: 0 },
  });
});

describe("Topbar — logout flow", () => {
  it("calls the logout endpoint and redirects to /login", async () => {
    const user = userEvent.setup();
    renderTopbar();

    await user.click(screen.getByRole("button", { name: /test user/i }));
    await user.click(screen.getByRole("button", { name: "Log out" }));

    await waitFor(() => expect(authApi.logout).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/login"));
  });
});
