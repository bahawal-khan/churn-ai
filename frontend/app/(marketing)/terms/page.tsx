import { Reveal } from "@/components/marketing/Reveal";

export default function TermsPage() {
  return (
    <div className="mx-auto grid max-w-4xl grid-cols-1 items-start gap-10 px-6 py-16 sm:py-20 lg:grid-cols-[1.2fr_0.8fr]">
      <Reveal>
        <h1 className="text-3xl font-bold text-text-primary sm:text-4xl">Terms of Service</h1>
        <span className="mt-3 inline-block rounded-pill bg-accent-primary-soft px-3 py-1 text-xs font-medium text-accent-primary">
          Please read these terms carefully.
        </span>
        <p className="mt-4 rounded-control bg-accent-primary-soft p-3 text-sm text-text-primary">
          This is placeholder legal copy pending real legal review — not a final terms document.
        </p>
        <div className="mt-6 space-y-4 text-sm text-text-muted">
          <p>
            By using ChurnAI you agree to use the platform for legitimate churn analysis on data you are authorized
            to process. ChurnAI&apos;s baseline model is provided for development and demonstration purposes and is
            not warranted as accurate for any specific market or population.
          </p>
          <p>A full terms of service document will be published here before production use.</p>
        </div>
      </Reveal>

      <Reveal delay={0.12} className="flex justify-center lg:justify-end">
        <div className="relative flex h-56 w-56 items-center justify-center rounded-full bg-gradient-to-br from-glow-blue/15 to-glow-cyan/15">
          <div className="flex h-28 w-28 items-center justify-center rounded-3xl bg-gradient-to-br from-glow-blue to-glow-cyan text-white shadow-[0_16px_40px_-14px_var(--glow-blue)]">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zM14 3v5h5" />
              <path d="M9 14l2 2 4-4" />
            </svg>
          </div>
        </div>
      </Reveal>
    </div>
  );
}
