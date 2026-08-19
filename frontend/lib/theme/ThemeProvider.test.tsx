import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { authApi } from "@/lib/api/auth";
import { ThemeProvider, useTheme } from "./ThemeProvider";

jest.mock("@/lib/api/auth", () => ({
  authApi: { updateProfile: jest.fn().mockResolvedValue({}) },
}));

function ThemeToggleHarness() {
  const { theme, setTheme } = useTheme();
  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>Toggle (current: {theme})</button>
  );
}

beforeEach(() => {
  document.cookie = "churnai_theme=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  document.documentElement.removeAttribute("data-theme");
  jest.clearAllMocks();
});

describe("ThemeProvider", () => {
  it("exposes the server-resolved initialTheme as the current theme, without mutating <html data-theme> itself", () => {
    // `<html data-theme>` is set by SSR/JSX in `app/layout.tsx` (via the
    // same `initialTheme` value), not by this component — asserting that
    // here would just be re-testing the old, hydration-mismatch-prone
    // behavior. What matters is that `theme` (and everything derived from
    // it, like the Sun/Moon icon) reflects `initialTheme` immediately.
    render(
      <ThemeProvider initialTheme="dark" isAuthenticated>
        <ThemeToggleHarness />
      </ThemeProvider>
    );
    expect(screen.getByRole("button")).toHaveTextContent("current: dark");
    expect(document.documentElement.getAttribute("data-theme")).toBeNull();
  });

  it("reconciles from a pre-paint script's DOM correction after mount, without a hydration warning", () => {
    // Simulates `app/layout.tsx`'s inline script flipping the DOM
    // attribute before React mounts (the one legitimate case
    // `initialTheme` can differ from what's on screen: an anonymous
    // visitor whose OS preference disagrees with the server's default).
    document.documentElement.setAttribute("data-theme", "light");
    render(
      <ThemeProvider initialTheme="dark" isAuthenticated={false}>
        <ThemeToggleHarness />
      </ThemeProvider>
    );
    expect(screen.getByRole("button")).toHaveTextContent("current: light");
  });

  it("toggling updates <html data-theme>, persists to a cookie, and (when authenticated) calls the server", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider initialTheme="dark" isAuthenticated>
        <ThemeToggleHarness />
      </ThemeProvider>
    );

    await user.click(screen.getByRole("button"));

    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(document.cookie).toContain("churnai_theme=light");
    expect(authApi.updateProfile).toHaveBeenCalledWith({ theme_preference: "light" });
  });

  it("does not call the server for an unauthenticated visitor", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider initialTheme="light" isAuthenticated={false}>
        <ThemeToggleHarness />
      </ThemeProvider>
    );

    await user.click(screen.getByRole("button"));

    expect(authApi.updateProfile).not.toHaveBeenCalled();
    expect(document.cookie).toMatch(/churnai_theme=(light|dark)/);
  });
});
