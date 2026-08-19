/** `docs/PROJECT_SPEC.md` §29 / `docs/FRONTEND_SPEC.md` §5: footer contact
 * links. Read from this single module so every page/footer instance stays
 * in sync. `footerNav` stays flat for any consumer that just wants the full
 * link list; `footerGroups` is the same links pre-split into the
 * Quick Links / Legal columns the redesigned footer renders. */
export const siteConfig = {
  name: "ChurnAI",
  tagline: "Predict. Understand. Retain.",
  developer: "Bahawal Khan",
  githubUrl: "https://github.com/bahawal-khan",
  linkedinUrl: "https://www.linkedin.com/in/bahawal-khan-9b1124313",
  contactEmail: "khanbahawal2004@gmail.com",
  footerNav: [
    { label: "About", href: "/about" },
    { label: "Features", href: "/#features" },
    { label: "FAQ", href: "/help" },
    { label: "Privacy", href: "/privacy" },
    { label: "Terms", href: "/terms" },
    { label: "Contact", href: "/contact" },
  ],
  footerGroups: {
    quickLinks: [
      { label: "Features", href: "/#features" },
      { label: "FAQ", href: "/help" },
      { label: "About", href: "/about" },
    ],
    legal: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
    ],
  },
};

export const SYNTHETIC_DATA_DISCLAIMER =
  "This model is trained on the IBM Telco benchmark dataset combined with synthetic Pakistani and " +
  "Indian customer data generated for development and demonstration purposes. It is not a validated " +
  "real-world model for any specific country or market, and the synthetic Pakistani/Indian data does " +
  "not prove real-world accuracy for customers in those countries. For production use, a company " +
  "should train a company-specific model on its own historical data via the Train Model feature.";

export const SHAP_DISCLAIMER =
  "This shows what the model learned from patterns in the data — it identifies correlation, not proven causation.";
