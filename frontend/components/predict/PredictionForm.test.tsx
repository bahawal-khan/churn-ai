import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PredictionForm } from "./PredictionForm";
import { ApiError } from "@/lib/api/client";
import type { FeatureSchemaField } from "@/lib/api/types";

const FIELDS: FeatureSchemaField[] = [
  { name: "Contract", dtype: "categorical", categories: ["Month-to-month", "One year", "Two year"] },
  { name: "Tenure Months", dtype: "numeric" },
];

describe("PredictionForm", () => {
  it("generates one field per feature_schema entry, using the right control per dtype", () => {
    render(<PredictionForm fields={FIELDS} onSubmit={jest.fn()} submitting={false} submitError={null} />);
    expect(screen.getByLabelText("Contract")).toBeInstanceOf(HTMLSelectElement);
    expect(screen.getByLabelText("Tenure Months")).toBeInstanceOf(HTMLInputElement);
  });

  it("submits numeric fields as numbers and categorical fields as the selected string", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<PredictionForm fields={FIELDS} onSubmit={onSubmit} submitting={false} submitError={null} />);

    await user.selectOptions(screen.getByLabelText("Contract"), "One year");
    await user.type(screen.getByLabelText("Tenure Months"), "24");
    await user.click(screen.getByRole("button", { name: "Predict Churn" }));

    expect(onSubmit).toHaveBeenCalledWith({ Contract: "One year", "Tenure Months": 24 });
  });

  it("shows missing-field detail inline for a SCHEMA_MISMATCH error, not a generic toast", () => {
    const error = new ApiError(
      {
        code: "SCHEMA_MISMATCH",
        message: "customer_data is missing required field(s): Contract.",
        details: { missing_fields: ["Contract"] },
      },
      422,
      "req-123"
    );
    render(<PredictionForm fields={FIELDS} onSubmit={jest.fn()} submitting={false} submitError={error} />);

    expect(screen.getByText(/missing required field/i)).toBeInTheDocument();
    expect(screen.getByText(/missing: contract/i)).toBeInTheDocument();
  });

  it("disables the submit button while submitting", () => {
    render(<PredictionForm fields={FIELDS} onSubmit={jest.fn()} submitting={true} submitError={null} />);
    expect(screen.getByRole("button", { name: "Predict Churn" })).toBeDisabled();
  });
});
