import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BatchPredictionPanel } from "./BatchPredictionPanel";
import { ToastProvider } from "@/components/ui/Toast";
import { predictionsApi } from "@/lib/api/predictions";

jest.mock("@/lib/api/predictions", () => ({
  predictionsApi: { predictBatch: jest.fn(), downloadBatchResults: jest.fn() },
}));

const RESULT = {
  batch_job_id: "batch-123",
  dataset_id: 1,
  summary: {
    batch_job_id: "batch-123",
    model_id: "random_forest_v1",
    algorithm: "random_forest" as const,
    id_column: "CustomerID",
    total_rows: 3,
    scored_rows: 3,
    failed_rows: 0,
    predicted_churners: 1,
    risk_level_counts: { low: 1, medium: 1, high: 1 },
  },
  quality_report: { checks: [] },
  results: [
    { churn_probability: 0.8, predicted_class: 1, risk_level: "high" as const, prediction_error: null },
    { churn_probability: 0.4, predicted_class: 0, risk_level: "medium" as const, prediction_error: null },
    { churn_probability: 0.1, predicted_class: 0, risk_level: "low" as const, prediction_error: null },
  ],
};

function makeCsvFile() {
  return new File(["CustomerID,Contract\n1,Month-to-month\n"], "batch.csv", { type: "text/csv" });
}

describe("BatchPredictionPanel — reaches a completed state and enables download", () => {
  it("shows the summary and downloads results client-side once the batch call resolves", async () => {
    const user = userEvent.setup();
    (predictionsApi.predictBatch as jest.Mock).mockResolvedValue(RESULT);

    const createObjectURL = jest.fn().mockReturnValue("blob:mock-url");
    const revokeObjectURL = jest.fn();
    window.URL.createObjectURL = createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURL;

    render(
      <ToastProvider>
        <BatchPredictionPanel />
      </ToastProvider>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeCsvFile());

    expect(await screen.findByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("Total Rows").nextSibling).toHaveTextContent("3");

    const downloadButton = screen.getByRole("button", { name: "Download Results CSV" });
    expect(downloadButton).toBeEnabled();

    // Downloading builds the CSV from the already-fetched results in memory
    // rather than a second network call — this must work even when 0 rows
    // were successfully scored (nothing would be persisted server-side yet).
    await user.click(downloadButton);
    expect(predictionsApi.downloadBatchResults).not.toHaveBeenCalled();
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toContain("text/csv");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("shows a per-field failure summary and highlights failed rows without any fake probability", async () => {
    const user = userEvent.setup();
    (predictionsApi.predictBatch as jest.Mock).mockResolvedValue({
      ...RESULT,
      summary: { ...RESULT.summary, scored_rows: 0, failed_rows: 2, predicted_churners: 0 },
      results: [
        {
          churn_probability: null,
          predicted_class: null,
          risk_level: null,
          prediction_error: "Contract: Must be one of ['Month-to-month', 'One year', 'Two year'], got 'No'.",
        },
        {
          churn_probability: null,
          predicted_class: null,
          risk_level: null,
          prediction_error: "Contract: Must be one of ['Month-to-month', 'One year', 'Two year'], got 'Yes'.",
        },
      ],
    });

    render(
      <ToastProvider>
        <BatchPredictionPanel />
      </ToastProvider>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeCsvFile());

    expect(await screen.findByText("Why rows failed")).toBeInTheDocument();
    expect(screen.getByText("2 rows")).toBeInTheDocument();
    expect(screen.getAllByText("Unscored").length).toBeGreaterThan(0);
    expect(screen.queryByText(/^\d+\.\d%$/)).not.toBeInTheDocument();
  });
});
