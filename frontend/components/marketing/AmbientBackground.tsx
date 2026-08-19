/** `Design.md`: subtle layered gradient glow + faint flowing lines behind
 * every public page. Pure CSS/SVG (no client JS needed), `aria-hidden` and
 * `pointer-events-none` so it never interferes with content or a11y, and
 * absolutely positioned within the marketing layout's `relative isolate`
 * wrapper so it never affects document flow/layout of real content. */
export function AmbientBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute left-1/2 top-[-12rem] h-[34rem] w-[34rem] -translate-x-1/2 rounded-full bg-glow-purple opacity-[var(--marketing-glow-opacity)] blur-[110px] animate-drift-slow" />
      <div className="absolute right-[-10rem] top-[8rem] h-[26rem] w-[26rem] rounded-full bg-glow-cyan opacity-[var(--marketing-glow-opacity)] blur-[100px] animate-drift-slower" />
      <div className="absolute left-[-8rem] bottom-[4rem] h-[28rem] w-[28rem] rounded-full bg-glow-blue opacity-[var(--marketing-glow-opacity)] blur-[100px] animate-drift-slow" />
      <div className="absolute right-[6rem] bottom-[-8rem] h-[22rem] w-[22rem] rounded-full bg-glow-pink opacity-[calc(var(--marketing-glow-opacity)*0.7)] blur-[100px] animate-drift-slower" />

      <svg className="absolute inset-0 h-full w-full opacity-[0.35]" preserveAspectRatio="none">
        <defs>
          <linearGradient id="marketing-flow-line" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--glow-purple)" stopOpacity="0" />
            <stop offset="50%" stopColor="var(--glow-blue)" stopOpacity="0.7" />
            <stop offset="100%" stopColor="var(--glow-cyan)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d="M -100 120 C 300 40, 700 260, 1100 100 S 1700 220, 2000 80"
          fill="none"
          stroke="url(#marketing-flow-line)"
          strokeWidth="1.5"
          strokeDasharray="6 14"
          className="animate-flow-line"
        />
        <path
          d="M -100 480 C 320 560, 680 340, 1080 500 S 1680 380, 2000 520"
          fill="none"
          stroke="url(#marketing-flow-line)"
          strokeWidth="1.5"
          strokeDasharray="4 18"
          className="animate-flow-line"
        />
      </svg>
    </div>
  );
}
