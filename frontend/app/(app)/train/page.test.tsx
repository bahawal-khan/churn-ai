import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import TrainPage from "./page";
import { ToastProvider } from "@/components/ui/Toast";
import { datasetsApi } from "@/lib/api/datasets";
import { trainingApi } from "@/lib/api/training";
import { ApiError } from "@/lib/api/client";

function renderTrainPage() {
  return render(
    <ToastProvider>
      <TrainPage />
    </ToastProvider>
  );
}

jest.mock("@/lib/api/datasets", () => ({
  datasetsApi: { list: jest.fn() },
}));
jest.mock("@/lib/api/training", () => ({
  trainingApi: { list: jest.fn(), start: jest.fn(), get: jest.fn() },
  TERMINAL_TRAINING_STATUSES: ["completed", "failed"],
}));
jest.mock("@/lib/api/models", () => ({
  modelsApi: { activate: jest.fn() },
}));

const DATASET = {
  id: 1,
  organization_id: 1,
  original_filename: "customers.csv",
  source_type: "company_upload" as const,
  row_count: 500,
  column_schema: [
    { name: "Contract", dtype: "categorical" as const },
    { name: "Churn Value", dtype: "numeric" as const },
  ],
  column_mapping: null,
  data_quality_report: { checks: [] },
  has_target_column: false,
  target_column_name: null,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  jest.clearAllMocks();
  (datasetsApi.list as jest.Mock).mockResolvedValue({
    data: [DATASET],
    pagination: { page: 1, page_size: 50, total: 1, total_pages: 1 },
  });
  (trainingApi.list as jest.Mock).mockResolvedValue({
    data: [],
    pagination: { page: 1, page_size: 10, total: 0, total_pages: 0 },
  });
});

describe("TrainPage — blocked without a valid target column", () => {
  it("disables Start Training until both a dataset and a target column are chosen", async () => {
    const user = userEvent.setup();
    renderTrainPage();

    const dropdown = await screen.findByLabelText("Dataset");
    expect(screen.getByRole("button", { name: "Start Training" })).toBeDisabled();

    await user.selectOptions(dropdown, "1");
    expect(screen.getByRole("button", { name: "Start Training" })).toBeDisabled();

    await user.selectOptions(screen.getByLabelText(/target column/i), "Churn Value");
    expect(screen.getByRole("button", { name: "Start Training" })).toBeEnabled();
  });

  it("shows the exact TRAINING_LABELS_REQUIRED blocking message and the baseline-model alternative", async () => {
    const user = userEvent.setup();
    (trainingApi.start as jest.Mock).mockRejectedValue(
      new ApiError(
        {
          code: "TRAINING_LABELS_REQUIRED",
          message:
            "Training requires historical outcomes (which customers churned) so the model can learn patterns. Your file doesn't appear to include a churn/outcome column.",
          details: { reason: "target_column_not_found" },
        },
        422,
        null
      )
    );

    renderTrainPage();

    await user.selectOptions(await screen.findByLabelText("Dataset"), "1");
    await user.selectOptions(screen.getByLabelText(/target column/i), "Contract");
    await user.click(screen.getByRole("button", { name: "Start Training" }));

    expect(await screen.findByText(/training requires historical outcomes/i)).toBeInTheDocument();
    expect(screen.getByText(/you can still use the baseline model for predictions/i)).toBeInTheDocument();
  });
});
