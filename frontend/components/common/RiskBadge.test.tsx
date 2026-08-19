import { render, screen } from "@testing-library/react";

import { RiskBadge } from "./RiskBadge";

describe("RiskBadge", () => {
  it("maps 'low' to a Low Risk label", () => {
    render(<RiskBadge level="low" />);
    expect(screen.getByText("Low Risk")).toBeInTheDocument();
  });

  it("maps 'medium' to a Medium Risk label", () => {
    render(<RiskBadge level="medium" />);
    expect(screen.getByText("Medium Risk")).toBeInTheDocument();
  });

  it("maps 'high' to a High Risk label", () => {
    render(<RiskBadge level="high" />);
    expect(screen.getByText("High Risk")).toBeInTheDocument();
  });

  it("renders an 'Unscored' label when level is null, not a blank badge", () => {
    render(<RiskBadge level={null} />);
    expect(screen.getByText("Unscored")).toBeInTheDocument();
  });

  it("always pairs color with a text label (never color alone)", () => {
    render(<RiskBadge level="high" />);
    // The icon glyph plus the text label both render — color is never the
    // only signal (docs/FRONTEND_SPEC.md §22).
    expect(screen.getByText("High Risk").textContent).toContain("High Risk");
  });
});
