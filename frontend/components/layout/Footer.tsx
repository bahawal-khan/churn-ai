import Link from "next/link";

import { Icon } from "@/components/icons";
import { siteConfig } from "@/lib/siteConfig";
import { cn } from "@/lib/utils";

/** `docs/FRONTEND_SPEC.md` §5: present on every page. `compact` is used in
 * the authenticated app shell where vertical space is constrained — that
 * variant is intentionally left as the original plain layout (`Design.md`'s
 * redesign is scoped to public pages only). The full public-site footer
 * below mirrors the reference image's four-column layout: brand, Quick
 * Links, Legal, Connect. */
export function Footer({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <footer className="border-t border-border-subtle bg-bg-surface px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-text-muted">
          {siteConfig.footerNav.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-text-primary">
              {item.label}
            </Link>
          ))}
        </div>
      </footer>
    );
  }

  return (
    <footer className="relative border-t border-marketing-border bg-marketing-surface-solid/60 px-6 py-14 backdrop-blur-sm">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-10 sm:grid-cols-4">
        <div className="col-span-2 sm:col-span-1">
          <Link href="/" className="flex items-center gap-2 font-bold text-text-primary">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-glow-purple to-glow-blue text-xs text-white">
              C
            </div>
            {siteConfig.name}
          </Link>
          <p className="mt-2 text-sm text-text-muted">{siteConfig.tagline}</p>
          <p className="mt-3 max-w-xs text-xs text-text-muted">
            AI-powered churn prediction and retention intelligence platform for subscription and
            recurring-revenue businesses.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-text-primary">Quick Links</h3>
          <ul className="mt-3 flex flex-col gap-2 text-sm text-text-muted">
            {siteConfig.footerGroups.quickLinks.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="transition-colors hover:text-text-primary">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-text-primary">Legal</h3>
          <ul className="mt-3 flex flex-col gap-2 text-sm text-text-muted">
            {siteConfig.footerGroups.legal.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="transition-colors hover:text-text-primary">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-text-primary">Connect</h3>
          <ul className="mt-3 flex flex-col gap-3 text-sm text-text-muted">
            <li>
              <a
                href={`mailto:${siteConfig.contactEmail}`}
                className="flex items-center gap-2 transition-colors hover:text-text-primary"
              >
                <Icon name="mail" size={16} />
                {siteConfig.contactEmail}
              </a>
            </li>
            <li>
              <a
                href={siteConfig.linkedinUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 transition-colors hover:text-text-primary"
              >
                <Icon name="linkedin" size={16} />
                LinkedIn
              </a>
            </li>
            <li>
              <a
                href={siteConfig.githubUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 transition-colors hover:text-text-primary"
              >
                <Icon name="github" size={16} />
                GitHub
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div
        className={cn(
          "mx-auto mt-10 max-w-6xl border-t border-marketing-border pt-6 text-xs text-text-muted",
          "flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
        )}
      >
        <p>© {new Date().getFullYear()} {siteConfig.name}. All rights reserved.</p>
        <p>Developed by {siteConfig.developer}</p>
      </div>
    </footer>
  );
}
