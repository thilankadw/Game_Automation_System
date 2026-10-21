import type { ReactNode } from "react";

export type StatTone = "accent" | "info" | "violet" | "success";

export interface StatCardProps {
  label: string;
  value: string;
  meta: string;
  icon: ReactNode;
  tone?: StatTone;
}

/**
 * Compact metric tile used on the overview page.
 */
export function StatCard({
  label,
  value,
  meta,
  icon,
  tone = "accent",
}: StatCardProps) {
  return (
    <article className="stat-card" data-tone={tone}>
      <div className="stat-card-top">
        <span className="stat-label">{label}</span>
        <span className="stat-icon">{icon}</span>
      </div>
      <p className="stat-value">{value}</p>
      <p className="stat-meta">{meta}</p>
    </article>
  );
}
