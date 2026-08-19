import Link from "next/link";

import { AuthAwareCta } from "@/components/layout/AuthAwareCta";
import { IconTile, type IconTileColor } from "@/components/marketing/IconTile";
import { GlowCard } from "@/components/marketing/GlowCard";
import { Reveal } from "@/components/marketing/Reveal";
import { type IconName } from "@/components/icons";
import { buttonClasses } from "@/components/ui/buttonStyles";
import { cn } from "@/lib/utils";

const FEATURES: { title: string; description: string; icon: IconName; color: IconTileColor }[] = [
  {
    title: "AI-powered churn prediction",
    description: "Score customers individually or in bulk with a model trained on real behavioral patterns.",
    icon: "cpu",
    color: "blue",
  },
  {
    title: "SHAP explainability",
    description: "See exactly which factors are pushing each prediction up or down, ranked and visualized.",
    icon: "puzzle",
    color: "purple",
  },
  {
    title: "Company-specific model training",
    description: "Upload your own historical customer data and train a model tailored to your business.",
    icon: "train",
    color: "cyan",
  },
  {
    title: "Analytics dashboard",
    description: "Track churn risk, trends, and top drivers across your entire customer base at a glance.",
    icon: "analytics",
    color: "teal",
  },
];

const STEPS = [
  { title: "Upload", description: "Bring your customer data in as a CSV — validated and quality-checked automatically." },
  { title: "Train / Predict", description: "Train a model on your own outcomes, or predict with the baseline model instantly." },
  { title: "Understand via SHAP", description: "See the ranked factors behind every prediction, not just a number." },
  { title: "Act", description: "Prioritize outreach to your highest-risk, highest-value customers." },
];

export default function LandingPage() {
  return (
    <div>
      <section className="relative mx-auto max-w-6xl px-6 py-24 text-center sm:py-28">
        <Reveal>
          <h1 className="bg-gradient-to-br from-text-primary via-text-primary to-glow-purple bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-6xl">
            Predict. Understand. Retain.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-text-muted">
            ChurnAI is an AI-powered churn prediction and retention intelligence platform — know who is at risk, why,
            and what to do about it.
          </p>
          <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
            <AuthAwareCta
              loggedOutHref="/signup"
              loggedOutLabel="Sign Up Free"
              variant="primary"
              size="lg"
              className="bg-gradient-to-r from-glow-purple to-glow-blue shadow-[0_12px_32px_-12px_var(--glow-purple)] hover:opacity-90"
            />
            <Link href="/help" className={cn(buttonClasses("secondary", "lg"))}>
              See how it works
            </Link>
          </div>
        </Reveal>
      </section>

      <section id="features" className="relative mx-auto max-w-6xl px-6 py-16">
        <Reveal>
          <h2 className="text-center text-3xl font-bold text-text-primary">Key Features</h2>
          <p className="mx-auto mt-2 max-w-md text-center text-sm text-text-muted">
            Everything you need to predict, understand, and reduce customer churn.
          </p>
        </Reveal>
        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {FEATURES.map((feature, i) => (
            <Reveal key={feature.title} delay={i * 0.08}>
              <GlowCard>
                <IconTile icon={feature.icon} color={feature.color} />
                <h3 className="mt-4 text-base font-semibold text-text-primary">{feature.title}</h3>
                <p className="mt-2 text-sm text-text-muted">{feature.description}</p>
              </GlowCard>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="relative mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <h2 className="text-center text-3xl font-bold text-text-primary">How it works</h2>
        </Reveal>
        <div className="relative mt-12 grid grid-cols-1 gap-8 sm:grid-cols-4">
          <div
            aria-hidden
            className="absolute left-0 right-0 top-[18px] hidden h-px bg-gradient-to-r from-transparent via-marketing-border-hover to-transparent sm:block"
          />
          {STEPS.map((step, i) => (
            <Reveal key={step.title} delay={i * 0.08} className="relative flex flex-col items-center text-center">
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-glow-purple to-glow-blue text-sm font-bold text-white shadow-[0_6px_20px_-6px_var(--glow-purple)]">
                {i + 1}
              </div>
              <h3 className="text-sm font-semibold text-text-primary">{step.title}</h3>
              <p className="mt-1 text-xs text-text-muted">{step.description}</p>
            </Reveal>
          ))}
        </div>
      </section>
    </div>
  );
}
