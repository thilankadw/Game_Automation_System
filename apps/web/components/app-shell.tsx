import Link from "next/link";
import type { ReactNode } from "react";

import { NavLink } from "@/components/nav-link";
import {
  ActivityIcon,
  GamesIcon,
  LayersIcon,
  OverviewIcon,
  ProvidersIcon,
} from "@/components/icons";

const navigation = [
  { href: "/", label: "Overview", icon: <OverviewIcon /> },
  { href: "/games", label: "Games", icon: <GamesIcon /> },
  { href: "/providers", label: "Providers", icon: <ProvidersIcon /> },
];

/**
 * Application chrome with the brand, primary navigation, and main content area.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Link className="sidebar-brand" href="/">
          <span aria-hidden="true" className="brand-mark">
            GA
          </span>
          <span className="brand-copy">
            <span className="brand-title">Game Automation</span>
            <span className="brand-subtitle">Control plane</span>
          </span>
        </Link>

        <nav aria-label="Primary" className="sidebar-nav">
          <p className="nav-group-label">Workspace</p>
          <div className="nav-list">
            {navigation.map((item) => (
              <NavLink
                href={item.href}
                icon={item.icon}
                key={item.href}
                label={item.label}
              />
            ))}
          </div>

          <p className="nav-group-label">Operations</p>
          <div className="nav-list">
            <span className="nav-link nav-link-muted">
              <span className="nav-link-icon">
                <ActivityIcon />
              </span>
              <span>Automation runs</span>
              <span className="nav-soon">Soon</span>
            </span>
            <Link className="nav-link nav-link-muted" href="/providers">
              <span className="nav-link-icon">
                <LayersIcon />
              </span>
              <span>ROI sets</span>
            </Link>
          </div>
        </nav>

        <div className="sidebar-footer">
          <span aria-hidden="true" className="footer-pulse" />
          <div>
            <p className="footer-title">Local control plane</p>
            <p className="footer-meta">v0.1 · SQLite workspace</p>
          </div>
        </div>
      </aside>

      <main className="app-main">{children}</main>
    </div>
  );
}
