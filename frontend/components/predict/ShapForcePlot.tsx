import { Tooltip } from "@/components/ui/Tooltip";
import type { LocalExplanation } from "@/lib/api/predictions";
import { SHAP_DISCLAIMER } from "@/lib/siteConfig";
import { formatPercent, titleCase } from "@/lib/utils";

/** Base value -> ranked feature contributions -> final probability
 * (`docs/FRONTEND_SPEC.md` §12.3). Shared across single prediction, batch
 * row drill-down, and Customer Detail. */
export function ShapForcePlot({ explanation }: { explanation: LocalExplanation }) {
  const maxAbs = Math.max(...explanation.top_factors.map((f) => Math.abs(f.shap_value)), 0.0001);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>Base value: {formatPercent(explanation.base_value)}</span>
        {explanation.model_output !== undefined && <span>Final: {formatPercent(explanation.model_output)}</span>}
      </div>
      <ul className="flex flex-col gap-2">
        {explanation.top_factors.map((factor) => {
          const isIncrease = factor.direction === "increases_risk";
          const widthPct = (Math.abs(factor.shap_value) / maxAbs) * 100;
          return (
            <li key={factor.feature} className="flex items-center gap-3">
              <span className="w-32 shrink-0 truncate text-xs text-text-muted sm:w-40" title={factor.feature}>
                {titleCase(factor.feature)}
              </span>
              <div className="flex h-2 flex-1 items-center overflow-hidden rounded-pill bg-bg-elevated">
                <div
                  className="h-full rounded-pill"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: isIncrease ? "var(--risk-high)" : "var(--risk-low)",
                  }}
                />
              </div>
              <span className={`w-16 shrink-0 text-right text-xs font-medium ${isIncrease ? "text-risk-high" : "text-risk-low"}`}>
                {isIncrease ? "+" : "−"}
                {Math.abs(factor.shap_value * 100).toFixed(1)}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-text-muted">
        <Tooltip content={explanation.disclaimer ?? SHAP_DISCLAIMER}>What does this mean?</Tooltip>
      </p>
    </div>
  );
}
