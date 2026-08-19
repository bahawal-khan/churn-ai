/** Shared content source for inline `Tooltip`s and the `/help` glossary
 * (`docs/FRONTEND_SPEC.md` §8: "definitions are consistent everywhere they
 * appear"). Terms required by `docs/PROJECT_SPEC.md` §21. */
export interface GlossaryTerm {
  term: string;
  definition: string;
}

export const glossary: Record<string, GlossaryTerm> = {
  churn: {
    term: "Churn",
    definition: "A customer stopping their subscription or relationship with your business.",
  },
  churnProbability: {
    term: "Churn probability",
    definition:
      "The model's estimated likelihood (0-100%) that a given customer will churn, based on patterns learned from historical data.",
  },
  riskLevel: {
    term: "Risk level",
    definition:
      "A simplified Low / Medium / High label derived from the churn probability, using fixed thresholds (Low < 30%, Medium 30-60%, High ≥ 60%).",
  },
  shap: {
    term: "SHAP",
    definition:
      "SHapley Additive exPlanations — a method for explaining which factors pushed a prediction up or down, and by how much. It shows correlation the model learned, not proven causation.",
  },
  companySpecificTraining: {
    term: "Company-specific training",
    definition:
      "Training a churn model on your own historical customer data (including which customers actually churned), so predictions reflect your business instead of the generic baseline model.",
  },
  decisionThreshold: {
    term: "Decision threshold",
    definition: "The churn-probability cutoff above which a customer is classified as predicted to churn.",
  },
  baselineModel: {
    term: "Baseline model",
    definition:
      "The shared model ChurnAI ships with out of the box, trained on IBM benchmark + synthetic data. Not specific to your business until you train your own model.",
  },
};

export const faqEntries: GlossaryTerm[] = [
  { term: "What does churn mean?", definition: glossary.churn.definition },
  {
    term: "How do I upload data?",
    definition:
      "Go to Upload Data, drag in a .csv file (or click to browse). ChurnAI validates it, shows a preview and a data quality report, and tells you whether it can be used for predictions, training, or both.",
  },
  {
    term: "What data is required?",
    definition:
      "For predictions, your file needs the standard customer attribute columns (contract type, tenure, monthly charges, etc.) that ChurnAI's schema expects. For training, it additionally needs a historical churn outcome column.",
  },
  { term: "What does the probability number mean?", definition: glossary.churnProbability.definition },
  { term: "What does each risk level mean?", definition: glossary.riskLevel.definition },
  { term: "What does SHAP mean?", definition: glossary.shap.definition },
  {
    term: "What does company-specific training require, and why are labels mandatory?",
    definition:
      "It requires a dataset that includes which customers historically churned (a binary outcome column). Labels are mandatory because the model can only learn the patterns behind churn if it has real examples of customers who did and didn't churn — without labels there's nothing to learn from.",
  },
];
