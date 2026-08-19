import { Tooltip } from "@/components/ui/Tooltip";
import type { GlobalShapFeature } from "@/lib/api/models";
import { SHAP_DISCLAIMER } from "@/lib/siteConfig";
import { titleCase } from "@/lib/utils";

/** Global SHAP summary — "Top Churn Drivers" (`docs/PROJECT_SPEC.md` §19,
 * §15). Every SHAP surface carries the fixed disclaimer text verbatim. */
export function TopDriversBarList({ features }: { features: GlobalShapFeature[] }) {
  const max = Math.max(...features.map((f) => f.mean_abs_shap), 0.0001);

  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-2.5">
        {features.map((feature) => (
          <li key={feature.feature} className="flex items-center gap-3">
            <span className="w-32 shrink-0 truncate text-xs text-text-muted sm:w-40" title={feature.feature}>
              {titleCase(feature.feature)}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-pill bg-bg-elevated">
              <div
                className="h-full rounded-pill bg-accent-primary"
                style={{ width: `${(feature.mean_abs_shap / max) * 100}%` }}
              />
            </div>
            <span className="w-12 shrink-0 text-right text-xs text-text-muted">
              {(feature.mean_abs_shap * 100).toFixed(1)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-text-muted">
        <Tooltip content={SHAP_DISCLAIMER}>What does this mean?</Tooltip>
      </p>
    </div>
  );
}
