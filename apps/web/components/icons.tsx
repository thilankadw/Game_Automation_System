/**
 * Inline SVG icon set used across the dashboard.
 */

export interface IconProps {
  className?: string;
}

function IconFrame({
  className,
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      height="18"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
      width="18"
    >
      {children}
    </svg>
  );
}

/** Renders the overview grid icon. */
export function OverviewIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <rect height="7" rx="1.5" width="7" x="3" y="3" />
      <rect height="7" rx="1.5" width="7" x="14" y="3" />
      <rect height="7" rx="1.5" width="7" x="3" y="14" />
      <rect height="7" rx="1.5" width="7" x="14" y="14" />
    </IconFrame>
  );
}

/** Renders the games controller icon. */
export function GamesIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M7 8h10a4 4 0 0 1 4 4v2.5a3.5 3.5 0 0 1-6.2 2.2l-.8-1H10l-.8 1A3.5 3.5 0 0 1 3 14.5V12a4 4 0 0 1 4-4Z" />
      <path d="M8 11v3M6.5 12.5h3M15.5 11.5h.01M17.5 13.5h.01" />
    </IconFrame>
  );
}

/** Renders the provider server icon. */
export function ProvidersIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <rect height="6" rx="1.5" width="18" x="3" y="3" />
      <rect height="6" rx="1.5" width="18" x="3" y="15" />
      <path d="M7 6h.01M7 18h.01M12 6h5M12 18h5" />
    </IconFrame>
  );
}

/** Renders the ROI layers icon. */
export function LayersIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="m12 3 9 5-9 5-9-5 9-5Z" />
      <path d="m3 13 9 5 9-5" />
      <path d="m3 17 9 5 9-5" />
    </IconFrame>
  );
}

/** Renders the activity pulse icon. */
export function ActivityIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M3 12h4l2.5-7 5 14L17 12h4" />
    </IconFrame>
  );
}

/** Renders a right-pointing arrow. */
export function ArrowRightIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </IconFrame>
  );
}

/** Renders a left-pointing arrow. */
export function ArrowLeftIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </IconFrame>
  );
}

/** Renders an external link icon. */
export function ExternalLinkIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M14 4h6v6M20 4l-9 9" />
      <path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5" />
    </IconFrame>
  );
}

/** Renders the search magnifier icon. */
export function SearchIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </IconFrame>
  );
}

/** Renders the database cylinder icon. */
export function DatabaseIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7" />
    </IconFrame>
  );
}

/** Renders the crosshair icon used for ROI targeting. */
export function CrosshairIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
      <circle cx="12" cy="12" r="2" />
    </IconFrame>
  );
}

/** Renders a plus icon for create actions. */
export function PlusIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M12 5v14M5 12h14" />
    </IconFrame>
  );
}

/** Renders an X icon for dismissing dialogs. */
export function CloseIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="m6 6 12 12M18 6 6 18" />
    </IconFrame>
  );
}


