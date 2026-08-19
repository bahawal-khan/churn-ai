"use client";

import { cn } from "@/lib/utils";

export interface TabItem {
  value: string;
  label: string;
}

export function Tabs({
  items,
  value,
  onChange,
}: {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-border-subtle">
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={selected}
            onClick={() => onChange(item.value)}
            className={cn(
              "min-h-[44px] sm:min-h-0 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              selected
                ? "border-accent-primary text-accent-primary"
                : "border-transparent text-text-muted hover:text-text-primary"
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
