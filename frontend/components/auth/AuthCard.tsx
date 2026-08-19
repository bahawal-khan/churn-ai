import Link from "next/link";

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-app px-4 py-10">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-6 flex items-center justify-center gap-2 font-bold text-text-primary">
          <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent-primary text-sm text-white">
            C
          </div>
          ChurnAI
        </Link>
        <div className="rounded-card border border-border-subtle bg-bg-surface p-6 shadow-card sm:p-8">
          <h1 className="text-xl font-bold text-text-primary">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-text-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
        {footer && <div className="mt-4 text-center text-sm text-text-muted">{footer}</div>}
      </div>
    </div>
  );
}
