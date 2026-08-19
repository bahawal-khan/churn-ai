import { HeroGlyph } from "@/components/marketing/HeroGlyph";
import { IconTile, type IconTileColor } from "@/components/marketing/IconTile";
import { Reveal } from "@/components/marketing/Reveal";
import { type IconName } from "@/components/icons";
import { siteConfig } from "@/lib/siteConfig";

const TRAITS: { title: string; description: string; icon: IconName; color: IconTileColor }[] = [
  { title: "AI-Powered", description: "AI-powered customer churn prediction.", icon: "cpu", color: "purple" },
  { title: "Explainable", description: "A clear, SHAP-driven explanation of why.", icon: "puzzle", color: "pink" },
  { title: "Data-Driven", description: "Train a model on your own historical data.", icon: "upload", color: "blue" },
  { title: "Actionable", description: "Understand churn risk at a portfolio level.", icon: "target", color: "orange" },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-16 sm:py-20">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2">
        <Reveal>
          <h1 className="text-3xl font-bold text-text-primary sm:text-4xl">About ChurnAI</h1>
          <p className="mt-2 text-sm text-text-muted">{siteConfig.tagline}</p>
          <p className="mt-6 text-text-muted">
            ChurnAI is an AI-powered customer churn prediction and retention intelligence platform for
            subscription and recurring-revenue businesses. It helps you understand churn risk at a portfolio
            level, upload and validate your own customer data, train a model on your own historical outcomes,
            and predict — with a clear, SHAP-driven explanation of <em>why</em> — which customers are most
            likely to leave.
          </p>
          <p className="mt-4 text-text-muted">
            ChurnAI ships with a baseline model trained on the IBM Telco benchmark dataset combined with
            synthetic Pakistani and Indian development data. It does not claim to be a validated, real-world
            model for any specific country or market out of the box — its primary value is letting a company
            train its <strong>own</strong> model on its <strong>own</strong> historical data.
          </p>
        </Reveal>
        <Reveal delay={0.1} className="flex justify-center">
          <HeroGlyph className="h-64 w-64 sm:h-80 sm:w-80" />
        </Reveal>
      </div>

      <div className="mt-14 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {TRAITS.map((trait, i) => (
          <Reveal key={trait.title} delay={i * 0.06}>
            <div className="flex h-full flex-col items-start gap-3 rounded-2xl border border-marketing-border bg-marketing-surface-solid/60 p-5 shadow-marketing-card">
              <IconTile icon={trait.icon} color={trait.color} size="sm" />
              <h3 className="text-sm font-semibold text-text-primary">{trait.title}</h3>
              <p className="text-xs text-text-muted">{trait.description}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
