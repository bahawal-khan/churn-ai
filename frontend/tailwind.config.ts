import type { Config } from "tailwindcss";

// Semantic design tokens (`docs/FRONTEND_SPEC.md` §2): every color is a
// CSS variable defined per-theme in `styles/theme.css`, never a raw hex
// value in a component class.
const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-app": "var(--bg-app)",
        "bg-surface": "var(--bg-surface)",
        "bg-elevated": "var(--bg-elevated)",
        "text-primary": "var(--text-primary)",
        "text-muted": "var(--text-muted)",
        "text-inverse": "var(--text-inverse)",
        "border-subtle": "var(--border-subtle)",
        "border-strong": "var(--border-strong)",
        "accent-primary": "var(--accent-primary)",
        "accent-primary-hover": "var(--accent-primary-hover)",
        "accent-primary-soft": "var(--accent-primary-soft)",
        "risk-low": "var(--risk-low)",
        "risk-low-soft": "var(--risk-low-soft)",
        "risk-medium": "var(--risk-medium)",
        "risk-medium-soft": "var(--risk-medium-soft)",
        "risk-high": "var(--risk-high)",
        "risk-high-soft": "var(--risk-high-soft)",
        "danger": "var(--danger)",
        "danger-soft": "var(--danger-soft)",
        "success": "var(--success)",
        "focus-ring": "var(--focus-ring)",
        "glow-purple": "var(--glow-purple)",
        "glow-blue": "var(--glow-blue)",
        "glow-cyan": "var(--glow-cyan)",
        "glow-pink": "var(--glow-pink)",
        "glow-orange": "var(--glow-orange)",
        "glow-teal": "var(--glow-teal)",
        "marketing-bg": "var(--marketing-bg-app)",
        "marketing-surface": "var(--marketing-surface)",
        "marketing-surface-solid": "var(--marketing-surface-solid)",
        "marketing-border": "var(--marketing-border)",
        "marketing-border-hover": "var(--marketing-border-hover)",
      },
      borderRadius: {
        card: "var(--radius-card)",
        control: "var(--radius-control)",
        pill: "var(--radius-pill)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        elevated: "var(--shadow-elevated)",
        "marketing-card": "var(--marketing-shadow-card)",
        "marketing-hover": "var(--marketing-shadow-hover)",
      },
      fontSize: {
        "kpi": ["2rem", { lineHeight: "2.25rem", fontWeight: "700" }],
        "kpi-sm": ["1.5rem", { lineHeight: "1.875rem", fontWeight: "700" }],
      },
      spacing: {
        "4.5": "1.125rem",
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
        "slide-up": "slide-up 200ms ease-out",
        "drift-slow": "drift 22s ease-in-out infinite",
        "drift-slower": "drift 30s ease-in-out infinite reverse",
        "flow-line": "flow-line 16s linear infinite",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        drift: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(3%, -4%) scale(1.06)" },
        },
        "flow-line": {
          from: { strokeDashoffset: "0" },
          to: { strokeDashoffset: "-1000" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
