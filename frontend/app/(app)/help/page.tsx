"use client";

import { useState } from "react";

import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { faqEntries, glossary } from "@/lib/glossary";

export default function HelpPage() {
  const [tourOpen, setTourOpen] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Help & FAQ</h1>
        <p className="text-sm text-text-muted">Everything you need to get the most out of ChurnAI.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Guided Walkthrough</CardTitle>
        </CardHeader>
        <p className="mb-3 text-sm text-text-muted">Replay the first-time tour covering upload, predictions, risk, and SHAP.</p>
        <Button size="sm" onClick={() => setTourOpen(true)}>
          Start walkthrough
        </Button>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Frequently Asked Questions</CardTitle>
        </CardHeader>
        <dl className="flex flex-col gap-4">
          {faqEntries.map((entry) => (
            <div key={entry.term}>
              <dt className="text-sm font-semibold text-text-primary">{entry.term}</dt>
              <dd className="mt-1 text-sm text-text-muted">{entry.definition}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Glossary</CardTitle>
        </CardHeader>
        <dl className="flex flex-col gap-4">
          {Object.values(glossary).map((entry) => (
            <div key={entry.term}>
              <dt className="text-sm font-semibold text-text-primary">{entry.term}</dt>
              <dd className="mt-1 text-sm text-text-muted">{entry.definition}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {tourOpen && <OnboardingTour onDone={() => setTourOpen(false)} />}
    </div>
  );
}
