import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteButton } from "@/components/delete-button";
import { EmptyState } from "@/components/empty-state";
import { GameFormButton } from "@/components/game-form-button";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CameraIcon,
  CrosshairIcon,
  ExternalLinkIcon,
  ProvidersIcon,
} from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { RoiCaptureButton } from "@/components/roi-capture-button";
import { RoiSetFormButton } from "@/components/roi-set-form-button";
import { ScreenshotCaptureButton } from "@/components/screenshot-capture-button";
import { ScreenshotGallery } from "@/components/screenshot-gallery";
import {
  API_URL,
  ApiError,
  type Game,
  type GameProvider,
  type Roi,
  type ScreenshotCaptureSession,
  type StoredScreenshotSession,
  getAllProviders,
  getGame,
  getScreenshotCaptureSessions,
  getStoredScreenshots,
} from "@/lib/api";
import {
  formatDateTime,
  formatNumber,
  formatRoiName,
  formatUrlHost,
  getInitials,
} from "@/lib/format";

export const dynamic = "force-dynamic";

const FALLBACK_VIEWPORT = { width: 1152, height: 648 };

interface GameDetailPageProps {
  params: Promise<{ id: string }>;
}

/**
 * Clamp a viewport-relative percentage to the visible map area.
 */
function clampPercent(value: number): number {
  return Math.min(100, Math.max(0, value));
}

interface RoiPreviewProps {
  rois: Roi[];
  width: number;
  height: number;
  imageUrl: string | null;
}

/**
 * Draws the game's ROI boxes over the latest capture, or a grid when empty.
 */
function RoiPreview({ rois, width, height, imageUrl }: RoiPreviewProps) {
  return (
    <div
      aria-hidden="true"
      className="roi-map"
      style={{ aspectRatio: `${width} / ${height}` }}
    >
      {imageUrl ? (
        // The latest capture is decorative; the region list below is the
        // accessible representation of the same data.
        // eslint-disable-next-line @next/next/no-img-element
        <img alt="" className="roi-map-image" src={imageUrl} />
      ) : (
        <div className="roi-map-grid" />
      )}
      {rois.map((roi) => {
        const left = clampPercent((roi.x / width) * 100);
        const top = clampPercent((roi.y / height) * 100);
        const right = clampPercent(((roi.x + roi.width) / width) * 100);
        const bottom = clampPercent(((roi.y + roi.height) / height) * 100);
        const regionWidth = Math.max(0, right - left);
        const regionHeight = Math.max(0, bottom - top);

        if (regionWidth === 0 || regionHeight === 0) {
          return null;
        }

        return (
          <span
            className="roi-map-region"
            data-roi={roi.name}
            key={roi.id}
            style={{
              height: `${regionHeight}%`,
              left: `${left}%`,
              top: `${top}%`,
              width: `${regionWidth}%`,
            }}
            title={`${formatRoiName(roi.name)} · x ${roi.x}, y ${roi.y}, ${roi.width}×${roi.height}`}
          >
            <span className="roi-map-label">{formatRoiName(roi.name)}</span>
          </span>
        );
      })}
    </div>
  );
}

/**
 * Renders a game's provider, attached ROIs, configuration, and screenshots.
 */
export default async function GameDetailPage({ params }: GameDetailPageProps) {
  const { id } = await params;
  const gameId = Number.parseInt(id, 10);

  if (!Number.isFinite(gameId) || gameId <= 0) {
    notFound();
  }

  let game: Game;

  try {
    game = await getGame(gameId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    return (
      <>
        <Link className="page-back" href="/games">
          <ArrowLeftIcon /> All games
        </Link>
        <PageHeader
          description="The game workspace could not be loaded."
          eyebrow="Catalog"
          title="Game unavailable"
        />
        <div className="error-panel">
          <div>
            <p className="error-panel-title">API request failed</p>
            <p className="error-panel-text">
              Start the API server and reload this page to inspect the game.
            </p>
          </div>
        </div>
      </>
    );
  }

  const [providersResult, sessionsResult, storedResult] =
    await Promise.allSettled([
      getAllProviders(),
      getScreenshotCaptureSessions(),
      getStoredScreenshots(game.id),
    ]);

  const providers: GameProvider[] | null =
    providersResult.status === "fulfilled" ? providersResult.value : null;
  const provider =
    providers?.find((item) => item.id === game.game_provider_id) ?? null;
  const gameSessions: ScreenshotCaptureSession[] | null =
    sessionsResult.status === "fulfilled"
      ? sessionsResult.value.filter(
          (session) => session.game_id === game.id,
        )
      : null;
  const storedSessions: StoredScreenshotSession[] | null =
    storedResult.status === "fulfilled" ? storedResult.value : null;
  const totalCaptures =
    storedSessions?.reduce(
      (total, session) => total + session.screenshot_count,
      0,
    ) ?? null;
  const latestSession = storedSessions?.[0] ?? null;
  const latestScreenshot =
    latestSession && latestSession.screenshots.length > 0
      ? latestSession.screenshots[latestSession.screenshots.length - 1]
      : null;
  const latestScreenshotUrl = latestScreenshot
    ? `${API_URL}${latestScreenshot}`
    : null;
  const activeSessions =
    gameSessions?.filter(
      (session) =>
        session.status === "starting" || session.status === "running",
    ) ?? [];
  const roiWidth = latestSession?.width ?? FALLBACK_VIEWPORT.width;
  const roiHeight = latestSession?.height ?? FALLBACK_VIEWPORT.height;
  const providerRoiSet = game.roi_set;

  return (
    <>
      <Link className="page-back" href="/games">
        <ArrowLeftIcon /> All games
      </Link>

      <section className="provider-hero game-hero">
        <div className="provider-hero-main">
          <span className="provider-hero-avatar">
            {getInitials(game.name)}
          </span>
          <div className="provider-hero-copy">
            <p className="page-eyebrow">Game detail</p>
            <h1 className="game-hero-title">{game.name}</h1>
            <p className="game-hero-meta">
              {provider ? (
                <Link href={`/providers/${provider.id}`}>
                  {provider.name}
                  <ArrowRightIcon />
                </Link>
              ) : (
                <span>Provider #{game.game_provider_id}</span>
              )}
              <span aria-hidden="true">·</span>
              <a href={game.url} rel="noreferrer" target="_blank">
                {formatUrlHost(game.url)}
                <ExternalLinkIcon />
              </a>
            </p>
          </div>
        </div>

        <div className="game-hero-right">
          <div className="provider-hero-stats">
            <div className="hero-stat">
              <p className="hero-stat-value">
                {formatNumber(game.number_of_spins)}
              </p>
              <p className="hero-stat-label">Spins / run</p>
            </div>
            <div className="hero-stat">
              <p className="hero-stat-value">
                {formatNumber(game.spin_wait_seconds)}s
              </p>
              <p className="hero-stat-label">Spin wait</p>
            </div>
            <div className="hero-stat">
              <p className="hero-stat-value">
                {providerRoiSet
                  ? formatNumber(providerRoiSet.rois.length)
                  : "—"}
              </p>
              <p className="hero-stat-label">ROI regions</p>
            </div>
            <div className="hero-stat">
              <p className="hero-stat-value">
                {totalCaptures !== null
                  ? formatNumber(totalCaptures)
                  : "—"}
              </p>
              <p className="hero-stat-label">Captured frames</p>
            </div>
          </div>

          <div className="game-hero-actions">
            <a
              className="button"
              href={game.url}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLinkIcon /> Open game
            </a>
            <RoiCaptureButton gameId={game.id} gameName={game.name} />
            <ScreenshotCaptureButton
              apiBaseUrl={API_URL}
              gameId={game.id}
              gameName={game.name}
              triggerClassName="button button-primary"
            />
            <GameFormButton
              game={game}
              providers={providers ?? []}
              triggerClassName="button"
              triggerLabel="Edit game"
            />
          </div>
        </div>
      </section>

      <div className="game-detail-grid">
        <div className="game-detail-main">
          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">Capture layout</h2>
                <p className="card-subtitle">
                  Regions used to drive spins and read the game surface.
                </p>
              </div>
              {providerRoiSet ? (
                <span className="badge badge-accent">
                  {providerRoiSet.name}
                </span>
              ) : (
                <span className="badge badge-muted">Unassigned</span>
              )}
            </div>

            {providerRoiSet ? (
              <div className="card-body">
                {providerRoiSet.rois.length > 0 ? (
                  <>
                    <RoiPreview
                      height={roiHeight}
                      imageUrl={latestScreenshotUrl}
                      rois={providerRoiSet.rois}
                      width={roiWidth}
                    />
                    <div className="roi-map-caption">
                      <span>
                        Scaled to the latest capture at {roiWidth}×{roiHeight}
                      </span>
                      <span>
                        Set #{providerRoiSet.id} ·{" "}
                        {formatNumber(providerRoiSet.rois.length)} regions
                      </span>
                    </div>
                    <div className="roi-region-list">
                      {providerRoiSet.rois.map((roi) => (
                        <div className="roi-region" key={roi.id}>
                          <span
                            className="roi-region-name"
                            data-roi={roi.name}
                          >
                            {formatRoiName(roi.name)}
                          </span>
                          <span className="roi-region-coords">
                            x {roi.x} · y {roi.y} · {roi.width}×{roi.height}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <EmptyState
                    description="Add coordinates to this set before running a capture."
                    icon={<CrosshairIcon />}
                    title="ROI set has no regions"
                  />
                )}
                <div className="roi-card-footer">
                  <p className="form-hint">
                    Capture needs the spin button; other regions stay
                    available for future analysis.
                  </p>
                  <RoiSetFormButton
                    providerId={game.game_provider_id}
                    roiSet={providerRoiSet}
                    triggerClassName="button button-sm"
                    triggerLabel="Edit ROI set"
                  />
                </div>
              </div>
            ) : (
              <div className="card-body">
                <EmptyState
                  description="Assign a provider ROI set to give this game a capture layout."
                  icon={<CrosshairIcon />}
                  title="No ROI set attached"
                />
                <div className="empty-state-actions">
                  <GameFormButton
                    game={game}
                    providers={providers ?? []}
                    triggerLabel="Assign ROI set"
                  />
                </div>
              </div>
            )}
          </section>

          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">Screenshot library</h2>
                <p className="card-subtitle">
                  One black-and-white frame per spin, grouped by run.
                </p>
              </div>
              <span
                className={
                  storedSessions
                    ? "badge badge-accent"
                    : "badge badge-muted"
                }
              >
                {storedSessions && totalCaptures !== null
                  ? `${formatNumber(totalCaptures)} frames`
                  : "Unavailable"}
              </span>
            </div>

            {activeSessions.length > 0 ? (
              <div className="game-run-list">
                {activeSessions.map((session) => (
                  <div className="game-run" key={session.id}>
                    <div>
                      <p className="game-run-title">
                        Session {session.id.slice(0, 8)}
                      </p>
                      <p className="game-run-meta">
                        {formatNumber(session.completed_spins)} /{" "}
                        {formatNumber(session.total_spins)} spins ·{" "}
                        {session.spin_wait_seconds}s wait
                      </p>
                    </div>
                    <span className="badge badge-accent">
                      {session.status === "starting" ? "Starting" : "Running"}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}

            {storedSessions === null ? (
              <div className="card-body">
                <div className="error-panel">
                  <div>
                    <p className="error-panel-title">
                      Screenshot data unavailable
                    </p>
                    <p className="error-panel-text">
                      Start the API server and reload this page to load the
                      capture library.
                    </p>
                  </div>
                </div>
              </div>
            ) : storedSessions.length > 0 ? (
              <ScreenshotGallery
                apiBaseUrl={API_URL}
                gameId={game.id}
                gameName={game.name}
                sessions={storedSessions}
              />
            ) : (
              <EmptyState
                description="Run a capture to store one screenshot per spin in a fresh session folder."
                icon={<CameraIcon />}
                title="No screenshots yet"
              />
            )}
          </section>
        </div>

        <aside className="game-detail-side">
          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">Provider</h2>
                <p className="card-subtitle">
                  Owner of this title and its capture sets.
                </p>
              </div>
            </div>
            <div className="card-body">
              {provider ? (
                <div className="game-provider-card">
                  <span className="provider-avatar provider-avatar-lg">
                    {getInitials(provider.name)}
                  </span>
                  <div className="game-provider-copy">
                    <p className="provider-name">{provider.name}</p>
                    <p className="provider-meta">
                      Provider #{provider.id}
                    </p>
                  </div>
                  <Link
                    className="button button-sm"
                    href={`/providers/${provider.id}`}
                  >
                    Workspace <ArrowRightIcon />
                  </Link>
                </div>
              ) : (
                <EmptyState
                  description={
                    providers
                      ? "This game points at a provider that is no longer in the catalog."
                      : "Provider data could not be loaded from the API."
                  }
                  icon={<ProvidersIcon />}
                  title="Provider unavailable"
                />
              )}
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">Configuration</h2>
                <p className="card-subtitle">
                  Stored automation settings for this game.
                </p>
              </div>
            </div>
            <div className="card-body">
              <dl className="game-facts">
                <div className="game-fact">
                  <dt>Game ID</dt>
                  <dd>#{game.id}</dd>
                </div>
                <div className="game-fact">
                  <dt>Spins / run</dt>
                  <dd>{formatNumber(game.number_of_spins)}</dd>
                </div>
                <div className="game-fact">
                  <dt>Spin wait</dt>
                  <dd>{formatNumber(game.spin_wait_seconds)}s</dd>
                </div>
                <div className="game-fact">
                  <dt>ROI set</dt>
                  <dd>
                    {providerRoiSet ? providerRoiSet.name : "Not assigned"}
                  </dd>
                </div>
                <div className="game-fact game-fact-wide">
                  <dt>Game URL</dt>
                  <dd>
                    <a href={game.url} rel="noreferrer" target="_blank">
                      {game.url}
                    </a>
                  </dd>
                </div>
              </dl>
              <div className="game-danger-zone">
                <p className="form-hint">
                  Removing the game keeps its screenshot folder on disk.
                </p>
                <DeleteButton
                  id={game.id}
                  kind="game"
                  name={game.name}
                />
              </div>
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">Latest capture</h2>
                <p className="card-subtitle">
                  {latestSession
                    ? formatDateTime(latestSession.created_at)
                    : "Waiting for the first run."}
                </p>
              </div>
            </div>
            {latestScreenshotUrl && latestSession ? (
              <a
                className="game-latest-shot"
                href={latestScreenshotUrl}
                rel="noreferrer"
                target="_blank"
              >
                {/* The full-size PNG opens in a new tab. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt={`Latest capture for ${game.name}`}
                  src={latestScreenshotUrl}
                />
                <span className="game-latest-meta">
                  <span>
                    Spin {formatNumber(latestSession.screenshot_count)}
                  </span>
                  <span>
                    {latestSession.width}×{latestSession.height}
                  </span>
                </span>
              </a>
            ) : (
              <div className="card-body">
                <EmptyState
                  description="Capture a run to preview its most recent frame here."
                  icon={<CameraIcon />}
                  title="No capture yet"
                />
              </div>
            )}
          </section>
        </aside>
      </div>
    </>
  );
}
