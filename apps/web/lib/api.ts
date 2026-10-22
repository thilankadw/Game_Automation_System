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

/** UI elements that can be marked with a ROI. */
export type RoiName =
  | "canvas"
  | "spin_button"
  | "balance"
  | "bet"
  | "win";

export interface Roi {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Fields accepted when creating or replacing ROIs. */
export interface RoiInput {
  name: RoiName;
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

/** Fields accepted when creating or updating a ROI set. */
export interface RoiSetInput {
  name?: string;
  rois?: RoiInput[];
}

export interface Game {
  id: number;
  name: string;
  number_of_spins: number;
  spin_wait_seconds: number;
  url: string;
  game_provider_id: number;
  roi_set_id: number | null;
  roi_set: RoiSet | null;
}

/** Fields accepted when creating or updating a game. */
export interface GameInput {
  name: string;
  number_of_spins: number;
  spin_wait_seconds: number;
  url: string;
  game_provider_id: number;
  roi_set_id: number | null;
}

/** Fields accepted when creating or updating a game provider. */
export interface GameProviderInput {
  name: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/** A live Chrome window used to draw ROIs for a game. */
export interface RoiCaptureSession {
  id: string;
  game_id: number;
  game_name: string;
  provider_id: number;
  url: string;
  existing_roi_set_id: number | null;
  created_at: string;
}

/** Lifecycle of an automated screenshot run. */
export type ScreenshotCaptureStatus =
  | "starting"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/** Progress and output details for an automated screenshot run. */
export interface ScreenshotCaptureSession {
  id: string;
  game_id: number;
  game_name: string;
  url: string;
  roi_set_id: number;
  roi_set_name: string;
  total_spins: number;
  spin_wait_seconds: number;
  completed_spins: number;
  status: ScreenshotCaptureStatus;
  error: string | null;
  output_path: string;
  latest_screenshot: string | null;
  created_at: string;
  finished_at: string | null;
}

/** A capture folder persisted on disk with its screenshot URLs. */
export interface StoredScreenshotSession {
  id: string;
  created_at: string;
  screenshot_count: number;
  width: number;
  height: number;
  screenshots: string[];
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

/**
 * Extract a human-readable message from a FastAPI error payload.
 *
 * FastAPI returns a plain string for handled errors and an array of validation
 * objects for request errors, so both shapes need to be understood.
 */
function readErrorDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.flatMap((entry) => {
      if (
        typeof entry === "object" &&
        entry !== null &&
        "msg" in entry &&
        typeof entry.msg === "string"
      ) {
        return [entry.msg];
      }
      return [];
    });

    return messages.length > 0 ? messages.join(" ") : null;
  }

  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { headers: initHeaders, ...initOptions } = init ?? {};
  const headers = new Headers(initHeaders);
  headers.set("Accept", "application/json");
  if (initOptions.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...initOptions,
    headers,
    signal: initOptions.signal ?? AbortSignal.timeout(8000),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = readErrorDetail(body.detail) ?? detail;
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
 * Fetch a single game with its assigned ROI set and regions.
 */
export function getGame(gameId: number): Promise<Game> {
  return request<Game>(`/games/${gameId}`);
}

/**
 * Fetch screenshots persisted on disk for a game, newest session first.
 */
export function getStoredScreenshots(
  gameId: number,
): Promise<StoredScreenshotSession[]> {
  return request<StoredScreenshotSession[]>(`/games/${gameId}/screenshots`);
}

/**
 * Delete one stored screenshot session for a game.
 */
export function deleteStoredScreenshotSession(
  gameId: number,
  sessionId: string,
): Promise<void> {
  return request<void>(
    `/games/${gameId}/screenshots/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

/**
 * Delete every stored screenshot session for a game.
 */
export function deleteAllStoredScreenshots(gameId: number): Promise<void> {
  return request<void>(`/games/${gameId}/screenshots`, {
    method: "DELETE",
  });
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
 * Create a ROI set for a game provider.
 *
 * Omitting `name` lets the API generate the next "Option N" label.
 */
export function createRoiSet(
  providerId: number,
  input: RoiSetInput,
): Promise<RoiSet> {
  return request<RoiSet>(`/game-providers/${providerId}/roi-sets`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/**
 * Replace a ROI set's name and full list of regions.
 */
export function updateRoiSet(
  roiSetId: number,
  input: RoiSetInput,
): Promise<RoiSet> {
  return request<RoiSet>(`/roi-sets/${roiSetId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/**
 * Delete a ROI set and its regions.
 */
export function deleteRoiSet(roiSetId: number): Promise<void> {
  return request<void>(`/roi-sets/${roiSetId}`, { method: "DELETE" });
}

/**
 * Fetch the API health status.
 */
export function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

/**
 * Open a live Chrome window to play the game and draw its ROIs.
 *
 * Browser launch and page load can exceed the default request timeout, so
 * this call allows up to sixty seconds.
 */
export function startRoiCapture(gameId: number): Promise<RoiCaptureSession> {
  return request<RoiCaptureSession>("/roi-capture/sessions", {
    method: "POST",
    body: JSON.stringify({ game_id: gameId }),
    signal: AbortSignal.timeout(60000),
  });
}

/**
 * Fetch every live ROI capture session.
 */
export function getRoiCaptureSessions(): Promise<RoiCaptureSession[]> {
  return request<RoiCaptureSession[]>("/roi-capture/sessions");
}

/**
 * Fetch a single live ROI capture session.
 */
export function getRoiCaptureSession(
  sessionId: string,
): Promise<RoiCaptureSession> {
  return request<RoiCaptureSession>(
    `/roi-capture/sessions/${encodeURIComponent(sessionId)}`,
  );
}

/**
 * Close a live ROI capture session and its Chrome window.
 */
export function stopRoiCapture(sessionId: string): Promise<void> {
  return request<void>(
    `/roi-capture/sessions/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

/**
 * Start an automated spin-and-screenshot run for a game.
 */
export function startScreenshotCapture(
  gameId: number,
): Promise<ScreenshotCaptureSession> {
  return request<ScreenshotCaptureSession>("/screenshot-capture/sessions", {
    method: "POST",
    body: JSON.stringify({ game_id: gameId }),
  });
}

/**
 * Fetch every screenshot capture session.
 */
export function getScreenshotCaptureSessions(): Promise<
  ScreenshotCaptureSession[]
> {
  return request<ScreenshotCaptureSession[]>("/screenshot-capture/sessions");
}

/**
 * Fetch a screenshot capture session with its latest progress.
 */
export function getScreenshotCaptureSession(
  sessionId: string,
): Promise<ScreenshotCaptureSession> {
  return request<ScreenshotCaptureSession>(
    `/screenshot-capture/sessions/${encodeURIComponent(sessionId)}`,
  );
}

/**
 * Stop a running screenshot capture and close its Chrome context.
 */
export function stopScreenshotCapture(sessionId: string): Promise<void> {
  return request<void>(
    `/screenshot-capture/sessions/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

/**
 * Create a game.
 */
export function createGame(input: GameInput): Promise<Game> {
  return request<Game>("/games", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/**
 * Update a game.
 */
export function updateGame(
  gameId: number,
  input: GameInput,
): Promise<Game> {
  return request<Game>(`/games/${gameId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/**
 * Delete a game.
 */
export function deleteGame(gameId: number): Promise<void> {
  return request<void>(`/games/${gameId}`, { method: "DELETE" });
}

/**
 * Create a game provider.
 */
export function createProvider(
  input: GameProviderInput,
): Promise<GameProvider> {
  return request<GameProvider>("/game-providers", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/**
 * Update a game provider.
 */
export function updateProvider(
  providerId: number,
  input: GameProviderInput,
): Promise<GameProvider> {
  return request<GameProvider>(`/game-providers/${providerId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/**
 * Delete a game provider.
 */
export function deleteProvider(providerId: number): Promise<void> {
  return request<void>(`/game-providers/${providerId}`, {
    method: "DELETE",
  });
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
