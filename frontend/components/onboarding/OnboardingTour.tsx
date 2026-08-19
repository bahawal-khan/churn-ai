"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { authApi } from "@/lib/api/auth";

const STEPS = [
  {
    title: "Welcome to ChurnAI",
    body: "This quick tour covers the five things you'll use most. You can replay it anytime from Settings.",
  },
  {
    title: "Upload your data",
    body: "Upload Data lets you bring in a CSV of customers. ChurnAI validates it and shows a data quality report.",
  },
  {
    title: "Run predictions",
    body: "Predictions lets you score a single customer or a whole CSV at once, with a churn probability and risk level for each.",
  },
  {
    title: "Understand risk badges",
    body: "Every customer gets a Low, Medium, or High risk badge, based on their predicted churn probability.",
  },
  {
    title: "See why, with SHAP",
    body: "Every prediction includes a ranked list of the factors that pushed it up or down — not just a number.",
  },
  {
    title: "Train your own model",
    body: "Train Model lets you train a model on your own historical outcomes for more accurate, business-specific predictions.",
  },
];

export function OnboardingTour({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const isLast = step === STEPS.length - 1;

  async function finish() {
    try {
      await authApi.updateProfile({ onboarding_completed: true });
    } finally {
      onDone();
    }
  }

  return (
    <Modal
      open
      onClose={finish}
      title={STEPS[step].title}
      footer={
        <div className="flex w-full items-center justify-between">
          <Button variant="ghost" size="sm" onClick={finish}>
            Skip
          </Button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button variant="secondary" size="sm" onClick={() => setStep((s) => s - 1)}>
                Back
              </Button>
            )}
            <Button size="sm" onClick={isLast ? finish : () => setStep((s) => s + 1)}>
              {isLast ? "Done" : "Next"}
            </Button>
          </div>
        </div>
      }
    >
      <p className="text-text-muted">{STEPS[step].body}</p>
      <p className="mt-3 text-xs text-text-muted">
        Step {step + 1} of {STEPS.length}
      </p>
    </Modal>
  );
}
