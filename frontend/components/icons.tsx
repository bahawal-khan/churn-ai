import { cn } from "@/lib/utils";

export type IconName =
  | "dashboard"
  | "upload"
  | "train"
  | "predict"
  | "customers"
  | "analytics"
  | "models"
  | "reports"
  | "settings"
  | "help"
  | "menu"
  | "sun"
  | "moon"
  | "bell"
  | "chevronDown"
  | "chevronLeft"
  | "search"
  | "logout"
  | "close"
  | "check"
  | "alertTriangle"
  | "download"
  | "trash"
  | "cpu"
  | "puzzle"
  | "target"
  | "shieldCheck"
  | "send"
  | "mail"
  | "linkedin"
  | "github";

const PATHS: Record<IconName, string> = {
  dashboard: "M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z",
  upload: "M12 16V4m0 0l-4 4m4-4l4 4M4 20h16",
  train: "M4 7h16M4 12h16M4 17h10M18 17l2 2-2 2",
  predict: "M13 2L3 14h7l-1 8 10-12h-7l1-8z",
  customers: "M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m5-9.13a4 4 0 110 8 4 4 0 010-8zm6 4a3 3 0 100-6 3 3 0 000 6z",
  analytics: "M3 3v18h18M8 17V9m5 8V5m5 12v-6",
  models: "M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z",
  reports: "M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zM14 3v5h5",
  settings:
    "M10.3 2h3.4l.6 2.5a7.9 7.9 0 012 1.2l2.4-.9 1.7 3-2 1.7c.1.4.1.8.1 1.2s0 .8-.1 1.2l2 1.7-1.7 3-2.4-.9a7.9 7.9 0 01-2 1.2l-.6 2.5h-3.4l-.6-2.5a7.9 7.9 0 01-2-1.2l-2.4.9-1.7-3 2-1.7a6 6 0 010-2.4l-2-1.7 1.7-3 2.4.9a7.9 7.9 0 012-1.2L10.3 2zM12 15a3 3 0 100-6 3 3 0 000 6z",
  help: "M12 22a10 10 0 100-20 10 10 0 000 20zM9.5 9a2.5 2.5 0 015 .5c0 1.5-2 1.8-2.3 3.3M12 17h.01",
  menu: "M4 6h16M4 12h16M4 18h16",
  sun: "M12 17a5 5 0 100-10 5 5 0 000 10zM12 1v2m0 18v2M4.2 4.2l1.4 1.4m12.8 12.8l1.4 1.4M1 12h2m18 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z",
  bell: "M6 8a6 6 0 1112 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6zM9 18a3 3 0 006 0",
  chevronDown: "M6 9l6 6 6-6",
  chevronLeft: "M15 18l-6-6 6-6",
  search: "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.3-4.3",
  logout: "M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4m6 14l5-5-5-5m5 5H9",
  close: "M18 6L6 18M6 6l12 12",
  check: "M5 13l4 4L19 7",
  alertTriangle: "M12 9v4m0 4h.01M10.3 3.9L2.5 17a1.5 1.5 0 001.3 2.2h16.4a1.5 1.5 0 001.3-2.2L13.7 3.9a1.5 1.5 0 00-2.6 0z",
  download: "M12 3v12m0 0l-4-4m4 4l4-4M4 21h16",
  trash: "M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0l-1 14a2 2 0 01-2 2H7a2 2 0 01-2-2L4 6h16z",
  cpu: "M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M7 7h10v10H7z",
  puzzle:
    "M6 3h5v3a2 2 0 104 0V3h5a1 1 0 011 1v5h-3a2 2 0 100 4h3v5a1 1 0 01-1 1h-5v-3a2 2 0 10-4 0v3H6a1 1 0 01-1-1v-5h3a2 2 0 100-4H5V4a1 1 0 011-1z",
  target: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 17a5 5 0 100-10 5 5 0 000 10zM12 13a1 1 0 100-2 1 1 0 000 2z",
  shieldCheck: "M12 3l7 3v6c0 5-3.5 8.5-7 9.5C8.5 20.5 5 17 5 12V6l7-3zM9 12l2 2 4-4",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z",
  mail: "M4 4h16a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V5a1 1 0 011-1zM3 6l9 7 9-7",
  linkedin: "M4 4h16a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V5a1 1 0 011-1zM7 10v7M7 7v.01M11 17v-4a2 2 0 014 0v4M11 13v4",
  github:
    "M12 2a10 10 0 00-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 015 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0012 2z",
};

export function Icon({
  name,
  className,
  size = 18,
}: {
  name: IconName;
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("shrink-0", className)}
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
