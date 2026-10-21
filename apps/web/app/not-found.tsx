import Link from "next/link";

import { ArrowLeftIcon } from "@/components/icons";

/**
 * Renders the application 404 screen.
 */
export default function NotFound() {
  return (
    <section className="card">
      <div className="empty-state">
        <p className="page-eyebrow">404 / Not found</p>
        <h1 className="page-title">This route is off the grid</h1>
        <p className="empty-state-description">
          The provider or page you requested does not exist in the current
          workspace.
        </p>
        <Link className="button button-primary" href="/">
          <ArrowLeftIcon /> Back to overview
        </Link>
      </div>
    </section>
  );
}
