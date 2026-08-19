/** Decorative hero mark used on About/Home (`Design.md` reference image's
 * glowing cube illustration): a gradient "C" glyph with an orbiting ring and
 * soft glow. Purely decorative SVG, `aria-hidden`. */
export function HeroGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 320" className={className} aria-hidden>
      <defs>
        <linearGradient id="hero-glyph-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--glow-purple)" />
          <stop offset="55%" stopColor="var(--glow-blue)" />
          <stop offset="100%" stopColor="var(--glow-cyan)" />
        </linearGradient>
        <radialGradient id="hero-glyph-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--glow-purple)" stopOpacity="0.45" />
          <stop offset="100%" stopColor="var(--glow-purple)" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle cx="160" cy="160" r="150" fill="url(#hero-glyph-glow)" />
      <circle
        cx="160"
        cy="160"
        r="118"
        fill="none"
        stroke="url(#hero-glyph-fill)"
        strokeOpacity="0.35"
        strokeWidth="1"
        strokeDasharray="2 10"
        className="animate-drift-slower"
        style={{ transformOrigin: "160px 160px" }}
      />

      <rect
        x="92"
        y="92"
        width="136"
        height="136"
        rx="32"
        fill="url(#hero-glyph-fill)"
        className="animate-drift-slow"
        style={{ transformOrigin: "160px 160px" }}
      />
      <path
        d="M188 132a30 30 0 100 56"
        fill="none"
        stroke="white"
        strokeOpacity="0.9"
        strokeWidth="9"
        strokeLinecap="round"
      />

      <circle cx="248" cy="96" r="5" fill="var(--glow-cyan)" />
      <circle cx="78" cy="228" r="4" fill="var(--glow-pink)" />
      <circle cx="252" cy="220" r="3.5" fill="var(--glow-blue)" />
    </svg>
  );
}
