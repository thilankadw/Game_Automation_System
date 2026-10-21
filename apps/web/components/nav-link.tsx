"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export interface NavLinkProps {
  href: string;
  label: string;
  icon: ReactNode;
}

/**
 * Sidebar navigation link that highlights the active route.
 */
export function NavLink({ href, label, icon }: NavLinkProps) {
  const pathname = usePathname();
  const isActive =
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      aria-current={isActive ? "page" : undefined}
      className={`nav-link${isActive ? " is-active" : ""}`}
      href={href}
    >
      <span className="nav-link-icon">{icon}</span>
      <span>{label}</span>
    </Link>
  );
}
