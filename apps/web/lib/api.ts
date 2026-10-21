/**
 * Typed client for the Game Automation System API.
 *
 * All requests run on the server by default. The base URL is read from
 * `NEXT_PUBLIC_API_URL` so the same build can point at a local or hosted API.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export interface GameProvider {
  id: number;
  name: string;
}

export interface Roi {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface RoiSet {
  id: number;
  name: string;
  game_provider_id: number;
  rois: Roi[];
}

export interface Game {
  id: number;
  name: string;
  number_of_spins: number;
  url: string;
  game_provider_id: number;
  roi_set_id: number | null;
  roi_set: RoiSet | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface HealthStatus {
  status: string;
  database: string;
}

/**
 * Error thrown when the API returns a non-success status.
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
    signal: init?.signal ?? AbortSignal.timeout(8000),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep the HTTP status text when the body is not JSON.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

/**
 * Fetch a page of games, optionally filtered by name.
 */
export function getGamesPage(params: {
  name?: string;
  skip?: number;
  limit?: number;
}): Promise<Page<Game>> {
  return request<Page<Game>>(`/games${buildQuery(params)}`);
}

/**
 * Fetch a page of game providers, optionally filtered by name.
 */
export function getProvidersPage(params: {
  name?: string;
  skip?: number;
  limit?: number;
}): Promise<Page<GameProvider>> {
  return request<Page<GameProvider>>(
    `/game-providers${buildQuery(params)}`,
  );
}

/**
 * Fetch a single game provider.
 */
export function getProvider(providerId: number): Promise<GameProvider> {
  return request<GameProvider>(`/game-providers/${providerId}`);
}

/**
 * Fetch every ROI set owned by a game provider.
 */
export function getRoiSets(providerId: number): Promise<RoiSet[]> {
  return request<RoiSet[]>(`/game-providers/${providerId}/roi-sets`);
}

/**
 * Fetch the API health status.
 */
export function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

/**
 * Walk paginated API results until the reported total is reached or the
 * page cap is hit. The cap prevents runaway requests on unexpectedly large
 * catalogs during server rendering.
 */
async function getAllPages<T>(
  fetchPage: (skip: number) => Promise<Page<T>>,
  maxPages = 10,
): Promise<T[]> {
  const items: T[] = [];
  let skip = 0;

  for (let page = 0; page < maxPages; page += 1) {
    const result = await fetchPage(skip);
    items.push(...result.items);
    if (result.items.length === 0 || items.length >= result.total) {
      break;
    }
    skip += result.limit;
  }

  return items;
}

/**
 * Fetch all games, up to ten pages of 100 records.
 */
export function getAllGames(): Promise<Game[]> {
  return getAllPages((skip) => getGamesPage({ skip, limit: 100 }));
}

/**
 * Fetch all game providers, up to ten pages of 100 records.
 */
export function getAllProviders(): Promise<GameProvider[]> {
  return getAllPages((skip) => getProvidersPage({ skip, limit: 100 }));
}
