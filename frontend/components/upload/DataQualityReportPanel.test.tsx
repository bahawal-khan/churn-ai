import { render, screen } from "@testing-library/react";

import { DataQualityReportPanel } from "./DataQualityReportPanel";
import type { DataQualityReport } from "@/lib/api/datasets";

// A known-bad fixture: missing required columns (fail) and a duplicate-rows
// warning (warn), alongside one passing check — mirrors what
// `ml/data_quality/validator.py` produces for a malformed upload.
const BAD_FIXTURE_REPORT: DataQualityReport = {
  checks: [
    {
      name: "missing_required_columns",
      status: "fail",
      detail: { missing_columns: ["Contract", "Payment Method"] },
    },
    {
      name: "duplicate_rows",
      status: "warn",
      detail: { count: 3 },
    },
    {
      name: "missing_values",
      status: "pass",
      detail: {},
    },
  ],
};

describe("DataQualityReportPanel", () => {
  it("renders every check with its pass/warn/fail status", () => {
    render(<DataQualityReportPanel report={BAD_FIXTURE_REPORT} />);

    expect(screen.getByText("FAIL")).toBeInTheDocument();
    expect(screen.getByText("WARN")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
  });

  it("surfaces the plain-language detail for a failed check", () => {
    render(<DataQualityReportPanel report={BAD_FIXTURE_REPORT} />);
    expect(screen.getByText(/Contract, Payment Method/)).toBeInTheDocument();
  });

  it("shows a fallback message when there are no checks at all", () => {
    render(<DataQualityReportPanel report={{ checks: [] }} />);
    expect(screen.getByText(/no data quality checks were recorded/i)).toBeInTheDocument();
  });
});
