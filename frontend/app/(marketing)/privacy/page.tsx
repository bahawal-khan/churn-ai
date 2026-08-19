import { Reveal } from "@/components/marketing/Reveal";

export default function PrivacyPage() {
  return (
    <div className="mx-auto grid max-w-4xl grid-cols-1 items-start gap-10 px-6 py-16 sm:py-20 lg:grid-cols-[1.2fr_0.8fr]">
      <Reveal>
        <h1 className="text-3xl font-bold text-text-primary sm:text-4xl">Privacy Policy</h1>
        <span className="mt-3 inline-block rounded-pill bg-accent-primary-soft px-3 py-1 text-xs font-medium text-accent-primary">
          Your privacy is important to us.
        </span>
        <p className="mt-4 rounded-control bg-accent-primary-soft p-3 text-sm text-text-primary">
          This is placeholder legal copy pending real legal review — not a final policy.
        </p>
        <div className="mt-6 space-y-4 text-sm text-text-muted">
          <p>
            ChurnAI stores the account and customer data you upload in order to provide churn prediction and
            analytics functionality. Data is isolated per organization and never shared across accounts.
          </p>
          <p>
            Passwords are hashed and never stored or logged in plaintext. Session cookies are HttpOnly and scoped to
            this application only.
          </p>
          <p>A full privacy policy will be published here before production use.</p>
        </div>
      </Reveal>

      <Reveal delay={0.12} className="flex justify-center lg:justify-end">
        <div className="relative flex h-56 w-56 items-center justify-center rounded-full bg-gradient-to-br from-glow-purple/15 to-glow-blue/15">
          <div className="flex h-28 w-28 items-center justify-center rounded-3xl bg-gradient-to-br from-glow-purple to-glow-blue text-white shadow-[0_16px_40px_-14px_var(--glow-purple)]">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 3l7 3v6c0 5-3.5 8.5-7 9.5C8.5 20.5 5 17 5 12V6l7-3z" />
              <path d="M12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM9.5 17c.5-2 1.6-3 2.5-3s2 1 2.5 3" />
            </svg>
          </div>
        </div>
      </Reveal>
    </div>
  );
}
