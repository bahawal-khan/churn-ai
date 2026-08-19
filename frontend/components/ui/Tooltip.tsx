"use client";

import { useId, useState } from "react";

import { cn } from "@/lib/utils";

/** Inline domain-term tooltip (`docs/FRONTEND_SPEC.md` §8), content sourced
 * from `lib/glossary.ts` so wording stays consistent everywhere a term
 * first appears. */
export function Tooltip({ content, children }: { content: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className="relative inline-flex">
      <span
        tabIndex={0}
        aria-describedby={id}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="inline-flex cursor-help items-center border-b border-dotted border-text-muted"
      >
        {children}
      </span>
      {open && (
        <span
          id={id}
          role="tooltip"
          className={cn(
            "absolute bottom-full left-1/2 z-50 mb-2 w-56 -translate-x-1/2 rounded-control border border-border-subtle",
            "bg-bg-elevated p-2.5 text-xs text-text-primary shadow-elevated"
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
