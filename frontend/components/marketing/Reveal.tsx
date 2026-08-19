"use client";

import { motion } from "framer-motion";

/** `Design.md`: cards "drop/fade smoothly from the top when they enter the
 * viewport", kept subtle. `viewport.once` means it never re-triggers on
 * scroll-back-up (a distracting/unprofessional repeat), and the whole effect
 * collapses to an instant, non-animated appearance for
 * `prefers-reduced-motion` users via framer-motion's built-in support. */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
