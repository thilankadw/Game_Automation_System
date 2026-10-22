"use server";

import { revalidatePath } from "next/cache";

import type { ActionResult } from "@/lib/action-result";
import {
  type GameInput,
  type GameProvider,
  type GameProviderInput,
  type RoiInput,
  type RoiName,
  type RoiSet,
  type RoiSetInput,
  type ScreenshotCaptureSession,
  ApiError,
  createGame,
  createProvider,
  createRoiSet,
  deleteAllStoredScreenshots,
  deleteGame,
  deleteProvider,
  deleteRoiSet,
  deleteStoredScreenshotSession,
  getProvidersPage,
  getRoiSets,
  getScreenshotCaptureSession,
  startRoiCapture,
  startScreenshotCapture,
  stopScreenshotCapture,
  updateGame,
  updateProvider,
  updateRoiSet,
} from "@/lib/api";

/** Result of a screenshot capture action that returns session state. */
export type ScreenshotSessionResult =
  | { ok: true; session: ScreenshotCaptureSession }
  | { ok: false; error: string };

/** Result of loading a provider's ROI sets for the game form. */
export type RoiSetListResult =
  | { ok: true; roiSets: RoiSet[] }
  | { ok: false; error: string };

/** Convert an unknown failure into a message that is safe to show in the UI. */
function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong. Try again.";
}

/** Refresh every page that renders provider or game catalog data. */
function revalidateCatalog(): void {
  revalidatePath("/");
  revalidatePath("/games", "layout");
  revalidatePath("/providers", "layout");
}

/** Normalize and validate game form input before sending it to the API. */
function normalizeGameInput(input: GameInput): GameInput | string {
  const name = input.name.trim();
  const url = input.url.trim();

  if (!name) {
    return "Game name is required.";
  }
  if (!url) {
    return "Game URL is required.";
  }
  if (
    !Number.isInteger(input.game_provider_id) ||
    input.game_provider_id <= 0
  ) {
    return "Select a game provider.";
  }

  const spins = Number(input.number_of_spins);
  if (!Number.isInteger(spins) || spins < 0) {
    return "Number of spins must be a non-negative whole number.";
  }

  const spinWait = Number(input.spin_wait_seconds);
  if (!Number.isInteger(spinWait) || spinWait < 0) {
    return "Spin wait must be a non-negative whole number of seconds.";
  }

  return {
    name,
    url,
    number_of_spins: spins,
    spin_wait_seconds: spinWait,
    game_provider_id: input.game_provider_id,
    roi_set_id: input.roi_set_id ?? null,
  };
}

/** Normalize and validate a provider name before sending it to the API. */
function normalizeProviderInput(
  input: GameProviderInput,
): GameProviderInput | string {
  const name = input.name.trim();
  if (!name) {
    return "Provider name is required.";
  }
  return { name };
}

const ROI_NAMES: readonly RoiName[] = [
  "canvas",
  "spin_button",
  "balance",
  "bet",
  "win",
];

/** Normalize and validate ROI set input before sending it to the API. */
function normalizeRoiSetInput(
  input: RoiSetInput,
  requireName: boolean,
): RoiSetInput | string {
  const name = input.name?.trim() ?? "";

  if (requireName && !name) {
    return "ROI set name is required.";
  }
  if (name.length > 255) {
    return "ROI set name must be 255 characters or fewer.";
  }

  const rois: RoiInput[] = [];
  const seen = new Set<RoiName>();

  for (const roi of input.rois ?? []) {
    if (!ROI_NAMES.includes(roi.name)) {
      return "Unknown ROI region.";
    }
    if (seen.has(roi.name)) {
      return "Each ROI region can appear only once per set.";
    }
    seen.add(roi.name);

    if (
      !Number.isInteger(roi.x) ||
      !Number.isInteger(roi.y) ||
      !Number.isInteger(roi.width) ||
      !Number.isInteger(roi.height) ||
      roi.x < 0 ||
      roi.y < 0 ||
      roi.width <= 0 ||
      roi.height <= 0
    ) {
      return "ROI regions need whole-number coordinates, with x/y at least 0 and width/height above 0.";
    }

    rois.push({
      name: roi.name,
      x: roi.x,
      y: roi.y,
      width: roi.width,
      height: roi.height,
    });
  }

  return name ? { name, rois } : { rois };
}

/** Create a game from validated form input. */
export async function createGameAction(
  input: GameInput,
): Promise<ActionResult> {
  const normalized = normalizeGameInput(input);
  if (typeof normalized === "string") {
    return { ok: false, error: normalized };
  }

  try {
    await createGame(normalized);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Update a game from validated form input. */
export async function updateGameAction(
  gameId: number,
  input: GameInput,
): Promise<ActionResult> {
  const normalized = normalizeGameInput(input);
  if (typeof normalized === "string") {
    return { ok: false, error: normalized };
  }

  try {
    await updateGame(gameId, normalized);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Delete a game. */
export async function deleteGameAction(
  gameId: number,
): Promise<ActionResult> {
  try {
    await deleteGame(gameId);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Create a game provider. */
export async function createProviderAction(
  input: GameProviderInput,
): Promise<ActionResult> {
  const normalized = normalizeProviderInput(input);
  if (typeof normalized === "string") {
    return { ok: false, error: normalized };
  }

  try {
    await createProvider(normalized);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Update a game provider. */
export async function updateProviderAction(
  providerId: number,
  input: GameProviderInput,
): Promise<ActionResult> {
  const normalized = normalizeProviderInput(input);
  if (typeof normalized === "string") {
    return { ok: false, error: normalized };
  }

  try {
    await updateProvider(providerId, normalized);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Delete a game provider. */
export async function deleteProviderAction(
  providerId: number,
): Promise<ActionResult> {
  try {
    await deleteProvider(providerId);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Load a provider's ROI sets so a game can be assigned one. */
export async function getRoiSetsAction(
  providerId: number,
): Promise<RoiSetListResult> {
  try {
    return { ok: true, roiSets: await getRoiSets(providerId) };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Create a ROI set for a provider; a blank name lets the API auto-name it. */
export async function createRoiSetAction(
  providerId: number,
  input: RoiSetInput,
): Promise<ActionResult> {
  const normalized = normalizeRoiSetInput(input, false);
  if (typeof normalized === "string") {
    return { ok: false, error: normalized };
  }

  try {
    await createRoiSet(providerId, normalized);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Update a ROI set's name and regions. */
export async function updateRoiSetAction(
  roiSetId: number,
  input: RoiSetInput,
): Promise<ActionResult> {
  const normalized = normalizeRoiSetInput(input, true);
  if (typeof normalized === "string") {
    return { ok: false, error: normalized };
  }

  try {
    await updateRoiSet(roiSetId, normalized);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Delete a ROI set and its regions. */
export async function deleteRoiSetAction(
  roiSetId: number,
): Promise<ActionResult> {
  try {
    await deleteRoiSet(roiSetId);
    revalidateCatalog();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Open a headed Chrome window so the user can play and draw ROIs. */
export async function startRoiCaptureAction(
  gameId: number,
): Promise<ActionResult> {
  try {
    await startRoiCapture(gameId);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Start an automated screenshot run for a game. */
export async function startScreenshotCaptureAction(
  gameId: number,
): Promise<ScreenshotSessionResult> {
  try {
    const session = await startScreenshotCapture(gameId);
    return { ok: true, session };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Poll a screenshot run for its latest progress. */
export async function getScreenshotCaptureSessionAction(
  sessionId: string,
): Promise<ScreenshotSessionResult> {
  try {
    const session = await getScreenshotCaptureSession(sessionId);
    return { ok: true, session };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Stop a running screenshot capture. */
export async function stopScreenshotCaptureAction(
  sessionId: string,
): Promise<ActionResult> {
  try {
    await stopScreenshotCapture(sessionId);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Delete one stored screenshot session for a game. */
export async function deleteScreenshotSessionAction(
  gameId: number,
  sessionId: string,
): Promise<ActionResult> {
  const normalizedSessionId = sessionId.trim();
  if (!Number.isInteger(gameId) || gameId <= 0) {
    return { ok: false, error: "Select a valid game." };
  }
  if (!normalizedSessionId) {
    return { ok: false, error: "Select a screenshot session." };
  }

  try {
    await deleteStoredScreenshotSession(gameId, normalizedSessionId);
    revalidatePath(`/games/${gameId}`);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Delete every stored screenshot session for a game. */
export async function deleteAllScreenshotsAction(
  gameId: number,
): Promise<ActionResult> {
  if (!Number.isInteger(gameId) || gameId <= 0) {
    return { ok: false, error: "Select a valid game." };
  }

  try {
    await deleteAllStoredScreenshots(gameId);
    revalidatePath(`/games/${gameId}`);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: errorMessage(error) };
  }
}

/** Search providers by name for the game form's combobox. */
export async function searchProvidersAction(
  query: string,
): Promise<GameProvider[]> {
  try {
    const page = await getProvidersPage({
      name: query.trim() || undefined,
      limit: 50,
    });
    return page.items;
  } catch {
    return [];
  }
}
