import { GlowCard } from "@/components/marketing/GlowCard";
import { IconTile } from "@/components/marketing/IconTile";
import { Reveal } from "@/components/marketing/Reveal";
import { siteConfig } from "@/lib/siteConfig";

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 text-center sm:py-20">
      <Reveal>
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-glow-purple to-glow-blue text-white shadow-[0_12px_32px_-10px_var(--glow-purple)]">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </div>
        <h1 className="mt-5 text-3xl font-bold text-text-primary sm:text-4xl">Contact Us</h1>
        <p className="mt-2 text-sm text-text-muted">Have a question or feedback? We&apos;d love to hear from you.</p>
      </Reveal>

      <Reveal delay={0.1} className="mt-10">
        <GlowCard className="flex flex-col gap-4 text-left">
          <a
            href={`mailto:${siteConfig.contactEmail}`}
            className="flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-accent-primary-soft"
          >
            <IconTile icon="mail" color="blue" size="sm" />
            <div>
              <p className="text-xs text-text-muted">Email</p>
              <p className="text-sm font-medium text-text-primary">{siteConfig.contactEmail}</p>
            </div>
          </a>
          <a
            href={siteConfig.linkedinUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-accent-primary-soft"
          >
            <IconTile icon="linkedin" color="cyan" size="sm" />
            <div>
              <p className="text-xs text-text-muted">LinkedIn</p>
              <p className="text-sm font-medium text-text-primary">{siteConfig.linkedinUrl.replace(/^https?:\/\//, "")}</p>
            </div>
          </a>
          <a
            href={siteConfig.githubUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-accent-primary-soft"
          >
            <IconTile icon="github" color="purple" size="sm" />
            <div>
              <p className="text-xs text-text-muted">GitHub</p>
              <p className="text-sm font-medium text-text-primary">{siteConfig.githubUrl.replace(/^https?:\/\//, "")}</p>
            </div>
          </a>
        </GlowCard>
      </Reveal>

      <Reveal delay={0.16} className="mt-6">
        <p className="rounded-xl border border-marketing-border bg-accent-primary-soft px-4 py-3 text-xs text-text-primary">
          There&apos;s no ticketing system yet — every message goes straight to the team.
        </p>
      </Reveal>
    </div>
  );
}
