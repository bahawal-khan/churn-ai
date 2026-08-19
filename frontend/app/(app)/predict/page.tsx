"use client";

import { useState } from "react";

import { Tabs } from "@/components/ui/Tabs";
import { BatchPredictionPanel } from "@/components/predict/BatchPredictionPanel";
import { SinglePredictionPanel } from "@/components/predict/SinglePredictionPanel";

export default function PredictPage() {
  const [tab, setTab] = useState("single");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Predictions</h1>
        <p className="text-sm text-text-muted">Predict churn for a single customer, or score a whole CSV at once.</p>
      </div>

      <Tabs
        items={[
          { value: "single", label: "Single Prediction" },
          { value: "batch", label: "Batch Prediction" },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === "single" ? <SinglePredictionPanel /> : <BatchPredictionPanel />}
    </div>
  );
}
