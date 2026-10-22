/**
 * Formatting helpers shared by dashboard pages.
 */

const numberFormatter = new Intl.NumberFormat("en-US");
const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

/**
 * Format an integer with thousands separators.
 */
export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

/**
 * Format an ISO timestamp as a short, consistent US date and time.
 */
export function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateTimeFormatter.format(date);
}

/**
 * Turn a snake_case ROI name into a human-readable label.
 */
export function formatRoiName(name: string): string {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/**
 * Return the hostname of a URL, falling back to the raw value when invalid.
 */
export function formatUrlHost(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/**
 * Return the uppercase initials of a provider name.
 */
export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "??";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
