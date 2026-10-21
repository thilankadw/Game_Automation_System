import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import {
  ArrowLeftIcon,
  CrosshairIcon,
  ExternalLinkIcon,
  GamesIcon,
  LayersIcon,
} from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import {
  ApiError,
  type Game,
  type GameProvider,
  type RoiSet,
  getAllGames,
  getProvider,
  getRoiSets,
} from "@/lib/api";
import {
  formatNumber,
  formatRoiName,
  getInitials,
} from "@/lib/format";

export const dynamic = "force-dynamic";

interface ProviderPageProps {
  params: Promise<{ id: string }>;
}

/**
 * Renders a provider workspace with its ROI sets and assigned games.
 */
export default async function ProviderPage({ params }: ProviderPageProps) {
  const { id } = await params;
  const providerId = Number.parseInt(id, 10);

  if (!Number.isFinite(providerId) || providerId <= 0) {
    notFound();
  }

  let provider: GameProvider;

  try {
    provider = await getProvider(providerId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    return (
      <>
        <Link className="page-back" href="/providers">
          <ArrowLeftIcon /> All providers
        </Link>
        <PageHeader
          description="The provider workspace could not be loaded."
          eyebrow="Integration"
          title="Provider unavailable"
        />
        <div className="error-panel">
          <div>
            <p className="error-panel-title">API request failed</p>
            <p className="error-panel-text">
              Start the API server and reload this page to inspect the provider.
            </p>
          </div>
        </div>
      </>
    );
  }

  const [roiSetsResult, gamesResult] = await Promise.allSettled([
    getRoiSets(providerId),
    getAllGames(),
  ]);

  const roiSets: RoiSet[] | null =
    roiSetsResult.status === "fulfilled" ? roiSetsResult.value : null;
  const allGames: Game[] | null =
    gamesResult.status === "fulfilled" ? gamesResult.value : null;
  const providerGames =
    allGames?.filter((game) => game.game_provider_id === provider.id) ?? null;
  const totalSpins =
    providerGames?.reduce((total, game) => total + game.number_of_spins, 0) ??
    null;

  return (
    <>
      <Link className="page-back" href="/providers">
        <ArrowLeftIcon /> All providers
      </Link>

      <section className="provider-hero">
        <div className="provider-hero-main">
          <span className="provider-hero-avatar">
            {getInitials(provider.name)}
          </span>
          <div className="provider-hero-copy">
            <h2>{provider.name}</h2>
            <p>Provider #{provider.id} · integration workspace</p>
          </div>
        </div>
        <div className="provider-hero-stats">
          <div className="hero-stat">
            <p className="hero-stat-value">
              {roiSets !== null ? formatNumber(roiSets.length) : "—"}
            </p>
            <p className="hero-stat-label">ROI sets</p>
          </div>
          <div className="hero-stat">
            <p className="hero-stat-value">
              {providerGames !== null ? formatNumber(providerGames.length) : "—"}
            </p>
            <p className="hero-stat-label">Games</p>
          </div>
          <div className="hero-stat">
            <p className="hero-stat-value">
              {totalSpins !== null ? formatNumber(totalSpins) : "—"}
            </p>
            <p className="hero-stat-label">Spins</p>
          </div>
        </div>
      </section>

      <div className="section-heading">
        <div>
          <h2>ROI sets</h2>
          <p>Capture layouts available to this provider&apos;s games.</p>
        </div>
      </div>

      {roiSets && roiSets.length > 0 ? (
        <div className="roi-grid">
          {roiSets.map((roiSet) => (
            <article className="roi-card" key={roiSet.id}>
              <div className="roi-card-header">
                <div>
                  <h3 className="roi-name">{roiSet.name}</h3>
                  <p className="roi-coords">
                    Set #{roiSet.id} · provider #{roiSet.game_provider_id}
                  </p>
                </div>
                <span className="roi-count">
                  {roiSet.rois.length} region
                  {roiSet.rois.length === 1 ? "" : "s"}
                </span>
              </div>
              {roiSet.rois.length > 0 ? (
                <div className="roi-chips">
                  {roiSet.rois.map((roi) => (
                    <span className="roi-chip" key={roi.id}>
                      <strong>{formatRoiName(roi.name)}</strong>
                      <span>
                        {roi.x},{roi.y} · {roi.width}×{roi.height}
                      </span>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="roi-empty">No regions defined for this set.</p>
              )}
            </article>
          ))}
        </div>
      ) : (
        <section className="card">
          <EmptyState
            description={
              roiSets
                ? "Add a ROI set through the API to capture this provider's UI."
                : "Start the API server and reload this page to load ROI sets."
            }
            icon={<CrosshairIcon />}
            title={roiSets ? "No ROI sets yet" : "ROI data unavailable"}
          />
        </section>
      )}

      <div className="section-heading">
        <div>
          <h2>Games</h2>
          <p>Titles that point at this provider.</p>
        </div>
      </div>

      <section className="card">
        {providerGames && providerGames.length > 0 ? (
          <div className="card-body">
            <div className="provider-game-list">
              {providerGames.map((game) => (
                <a
                  className="provider-game"
                  href={game.url}
                  key={game.id}
                  rel="noreferrer"
                  target="_blank"
                >
                  <span>
                    <span className="provider-game-name">{game.name}</span>
                    <span className="provider-game-meta">
                      {formatNumber(game.number_of_spins)} spins ·{" "}
                      {game.roi_set ? game.roi_set.name : "No ROI set"}
                    </span>
                  </span>
                  <ExternalLinkIcon />
                </a>
              ))}
            </div>
          </div>
        ) : (
          <EmptyState
            description={
              providerGames
                ? "Assign a game to this provider through the API."
                : "Start the API server and reload this page to load games."
            }
            icon={providerGames ? <GamesIcon /> : <LayersIcon />}
            title={
              providerGames ? "No games assigned" : "Game data unavailable"
            }
          />
        )}
      </section>
    </>
  );
}
