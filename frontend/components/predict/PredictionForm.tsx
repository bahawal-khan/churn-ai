"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiError } from "@/lib/api/client";
import type { FeatureSchemaField } from "@/lib/api/types";
import { titleCase } from "@/lib/utils";

export interface PredictionFormProps {
  fields: FeatureSchemaField[];
  onSubmit: (customerData: Record<string, unknown>) => Promise<void>;
  submitting: boolean;
  submitError: ApiError | null;
}

/** Fields generated from the active model's `feature_schema`
 * (`docs/FRONTEND_SPEC.md` §12.1) so the form always matches what the
 * active model actually expects, rather than a hardcoded field list that
 * could drift. */
export function PredictionForm({ fields, onSubmit, submitting, submitError }: PredictionFormProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const fieldErrors = (submitError?.details.field_errors as Record<string, string> | undefined) ?? {};
  const missingFields = (submitError?.details.missing_fields as string[] | undefined) ?? [];

  function handleChange(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const customerData: Record<string, unknown> = {};
    for (const field of fields) {
      const raw = values[field.name];
      if (raw === undefined || raw === "") continue;
      customerData[field.name] = field.dtype === "numeric" ? Number(raw) : raw;
    }
    await onSubmit(customerData);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      {submitError && submitError.code === "SCHEMA_MISMATCH" && (
        <div className="rounded-control bg-danger-soft p-3 text-sm text-danger">
          <p>{submitError.message}</p>
          {missingFields.length > 0 && <p className="mt-1">Missing: {missingFields.join(", ")}</p>}
        </div>
      )}
      {submitError && submitError.code !== "SCHEMA_MISMATCH" && (
        <p role="alert" className="rounded-control bg-danger-soft p-2.5 text-sm text-danger">
          {submitError.message}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {fields.map((field) =>
          field.dtype === "categorical" ? (
            <Select
              key={field.name}
              label={titleCase(field.name)}
              placeholder="Select…"
              value={values[field.name] ?? ""}
              onChange={(e) => handleChange(field.name, e.target.value)}
              error={fieldErrors[field.name]}
              options={(field.categories ?? []).map((c) => ({ value: c, label: c }))}
            />
          ) : (
            <Input
              key={field.name}
              type="number"
              min={0}
              step="any"
              label={titleCase(field.name)}
              value={values[field.name] ?? ""}
              onChange={(e) => handleChange(field.name, e.target.value)}
              error={fieldErrors[field.name]}
            />
          )
        )}
      </div>

      <Button type="submit" loading={submitting} className="self-start">
        Predict Churn
      </Button>
    </form>
  );
}
