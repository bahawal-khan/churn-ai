import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UploadPage from "./page";
import { ToastProvider } from "@/components/ui/Toast";
import { datasetsApi } from "@/lib/api/datasets";

function renderUploadPage() {
  return render(
    <ToastProvider>
      <UploadPage />
    </ToastProvider>
  );
}

jest.mock("@/lib/api/datasets", () => ({
  datasetsApi: { upload: jest.fn(), list: jest.fn() },
}));

function makeCsvFile() {
  return new File(["Contract,Payment Method\nYes,Cash\n"], "bad_customers.csv", { type: "text/csv" });
}

// A known-bad fixture (`docs/FRONTEND_SPEC.md` §25): the backend's
// `DataQualityValidator` found missing required columns (fail) and a
// duplicate-rows warning, and the dataset has no usable target column.
const BAD_UPLOAD_RESULT = {
  dataset: {
    id: 7,
    organization_id: 1,
    original_filename: "bad_customers.csv",
    source_type: "company_upload" as const,
    row_count: 12,
    column_schema: [
      { name: "Contract", dtype: "categorical" as const },
      { name: "Payment Method", dtype: "categorical" as const },
    ],
    column_mapping: null,
    data_quality_report: { checks: [] },
    has_target_column: false,
    target_column_name: null,
    created_at: "2026-01-01T00:00:00Z",
  },
  quality_report: {
    checks: [
      { name: "missing_required_columns", status: "fail" as const, detail: { missing_columns: ["Tenure Months", "Monthly Charges"] } },
      { name: "duplicate_rows", status: "warn" as const, detail: { count: 2 } },
      { name: "missing_values", status: "pass" as const, detail: {} },
    ],
  },
  preview: [{ Contract: "Yes", "Payment Method": "Cash" }],
};

beforeEach(() => {
  jest.clearAllMocks();
  (datasetsApi.list as jest.Mock).mockResolvedValue({
    data: [],
    pagination: { page: 1, page_size: 10, total: 0, total_pages: 0 },
  });
});

describe("UploadPage — malformed CSV produces the correct data-quality state", () => {
  it("renders the fail/warn/pass checks and the no-target-column badge for a known-bad file", async () => {
    const user = userEvent.setup();
    (datasetsApi.upload as jest.Mock).mockResolvedValue(BAD_UPLOAD_RESULT);

    renderUploadPage();

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeCsvFile());

    expect(await screen.findByText("FAIL")).toBeInTheDocument();
    expect(screen.getByText("WARN")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
    expect(screen.getByText(/Tenure Months, Monthly Charges/)).toBeInTheDocument();
    expect(screen.getByText("No outcome column detected — can be used for predictions only")).toBeInTheDocument();
  });
});
