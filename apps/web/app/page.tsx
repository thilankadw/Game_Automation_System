import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import {
  ActivityIcon,
  ArrowRightIcon,
  CrosshairIcon,
  DatabaseIcon,
  ExternalLinkIcon,
  GamesIcon,
  LayersIcon,
  ProvidersIcon,
} from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import {
  type Game,
  type GameProvider,
  type HealthStatus,
  getAllGames,
  getAllProviders,
  getHealth,
  getRoiSets,
} from "@/lib/api";
import {
  formatNumber,
  formatUrlHost,
  getInitials,
} from "@/lib/format";

export const dynamic = "force-dynamic";

interface ProviderMetric {
  provider: GameProvider;
  games: number;
  roiSets: number | null;
}

interface OverviewData {
  games: Game[] | null;
  providers: GameProvider[] | null;
  providerMetrics: ProviderMetric[] | null;
  roiSetTotal: number | null;
  health: HealthStatus | null;
}

async function loadOverview(): Promise<OverviewData> {
  const [gamesResult, providersResult, healthResult] = await Promise.allSettled([
    getAllGames(),
    getAllProviders(),
    getHealth(),
  ]);

  const games = gamesResult.status === "fulfilled" ? gamesResult.value : null;
  const providers =
    providersResult.status === "fulfilled" ? providersResult.value : null;
  const health = healthResult.status === "fulfilled" ? healthResult.value : null;

  if (!providers) {
    return {
      games,
      providers,
      providerMetrics: null,
      roiSetTotal: null,
      health,
    };
  }

  const roiSetResults = await Promise.allSettled(
    providers.map((provider) => getRoiSets(provider.id)),
  );

  const roiSetsByProvider = new Map<number, number | null>();
  providers.forEach((provider, index) => {
    const result = roiSetResults[index];
    roiSetsByProvider.set(
      provider.id,
      result.status === "fulfilled" ? result.value.length : null,
    );
  });

  const providerMetrics = providers
    .map((provider) => ({
      provider,
      games: (games ?? []).filter(
        (game) => game.game_provider_id === provider.id,
      ).length,
      roiSets: roiSetsByProvider.get(provider.id) ?? null,
    }))
    .sort((a, b) => b.games - a.games);

  const roiSetValues = providerMetrics.map((metric) => metric.roiSets);
  const roiSetTotal = roiSetValues.every(
    (value): value is number => value !== null,
  )
    ? roiSetValues.reduce((total, value) => total + value, 0)
    : null;

  return { games, providers, providerMetrics, roiSetTotal, health };
}

function providerNameFor(game: Game, providers: GameProvider[] | null): string {
  return (
    providers?.find((provider) => provider.id === game.game_provider_id)?.name ??
    `Provider #${game.game_provider_id}`
  );
}

/**
 * Renders the live overview of games, providers, ROI sets, and system health.
 */
export default async function Home() {
  const { games, providers, providerMetrics, roiSetTotal, health } =
    await loadOverview();

  const recentGames = games
    ? [...games].sort((a, b) => b.id - a.id).slice(0, 6)
    : [];
  const totalSpins = games?.reduce(
    (total, game) => total + game.number_of_spins,
    0,
  );
  const apiOnline = games !== null || providers !== null;
  const maxGames = Math.max(
    1,
    ...(providerMetrics?.map((metric) => metric.games) ?? [0]),
  );

  return (
    <>
      <PageHeader
        actions={
          <span className="status-pill" data-online={apiOnline}>
            {apiOnline ? "API connected" : "API offline"}
          </span>
        }
        description="A live snapshot of your game catalog, provider integrations, and automation coverage."
        eyebrow="Overview"
        title="Automation control plane"
      />

      <section aria-label="Platform metrics" className="stats-grid">
        <StatCard
          icon={<GamesIcon />}
          label="Games"
          meta={
            games
              ? `${formatNumber(games.length)} configured titles`
              : "Catalog unavailable"
          }
          tone="accent"
          value={games ? formatNumber(games.length) : "—"}
        />
        <StatCard
          icon={<ProvidersIcon />}
          label="Providers"
          meta={
            providers
              ? `${formatNumber(providers.length)} active integrations`
              : "Providers unavailable"
          }
          tone="info"
          value={providers ? formatNumber(providers.length) : "—"}
        />
        <StatCard
          icon={<LayersIcon />}
          label="ROI sets"
          meta={
            roiSetTotal !== null
              ? `${formatNumber(roiSetTotal)} capture layouts`
              : "Layout data unavailable"
          }
          tone="violet"
          value={roiSetTotal !== null ? formatNumber(roiSetTotal) : "—"}
        />
        <StatCard
          icon={<ActivityIcon />}
          label="Configured spins"
          meta={
            totalSpins !== undefined
              ? `Across ${formatNumber(games?.length ?? 0)} games`
              : "Spin data unavailable"
          }
          tone="success"
          value={totalSpins !== undefined ? formatNumber(totalSpins) : "—"}
        />
      </section>

      <div className="dashboard-grid">
        <section className="card">
          <div className="card-header">
            <div className="card-title-group">
              <h2 className="card-title">Recent games</h2>
              <p className="card-subtitle">
                Latest entries in the automation catalog
              </p>
            </div>
            <Link className="card-link" href="/games">
              View all <ArrowRightIcon />
            </Link>
          </div>
          {recentGames.length > 0 ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Game</th>
                    <th scope="col">Provider</th>
                    <th className="numeric" scope="col">
                      Spins
                    </th>
                    <th scope="col">ROI set</th>
                  </tr>
                </thead>
                <tbody>
                  {recentGames.map((game) => (
                    <tr key={game.id}>
                      <td>
                        <a
                          className="game-link"
                          href={game.url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {game.name}
                          <ExternalLinkIcon />
                        </a>
                        <span className="table-secondary">
                          {formatUrlHost(game.url)}
                        </span>
                      </td>
                      <td>{providerNameFor(game, providers)}</td>
                      <td className="numeric">
                        {formatNumber(game.number_of_spins)}
                      </td>
                      <td>
                        {game.roi_set ? (
                          <span className="badge badge-accent">
                            {game.roi_set.name}
                          </span>
                        ) : (
                          <span className="badge badge-muted">Unassigned</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              description={
                apiOnline
                  ? "Create a game through the API to populate the catalog."
                  : "Start the API server and reload the dashboard to load games."
              }
              icon={<DatabaseIcon />}
              title={apiOnline ? "No games yet" : "API unreachable"}
            />
          )}
        </section>

        <div className="dashboard-column">
          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">Provider coverage</h2>
                <p className="card-subtitle">Games and layouts by provider</p>
              </div>
              <Link className="card-link" href="/providers">
                All <ArrowRightIcon />
              </Link>
            </div>
            {providerMetrics && providerMetrics.length > 0 ? (
              <div className="provider-list">
                {providerMetrics.slice(0, 6).map((metric) => (
                  <Link
                    className="provider-row"
                    href={`/providers/${metric.provider.id}`}
                    key={metric.provider.id}
                  >
                    <span className="provider-avatar">
                      {getInitials(metric.provider.name)}
                    </span>
                    <span className="provider-info">
                      <p className="provider-name">{metric.provider.name}</p>
                      <p className="provider-meta">
                        {formatNumber(metric.games)} games ·{" "}
                        {metric.roiSets !== null
                          ? `${formatNumber(metric.roiSets)} ROI sets`
                          : "ROI data unavailable"}
                      </p>
                    </span>
                    <span className="provider-bar">
                      <span className="provider-count">
                        {formatNumber(metric.games)}
                      </span>
                      <span className="provider-bar-track">
                        <span
                          className="provider-bar-fill"
                          style={{
                            width: `${Math.max(
                              6,
                              (metric.games / maxGames) * 100,
                            )}%`,
                          }}
                        />
                      </span>
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState
                description={
                  apiOnline
                    ? "Add a provider to start grouping games and ROI sets."
                    : "Start the API server to load provider coverage."
                }
                icon={<ProvidersIcon />}
                title={apiOnline ? "No providers yet" : "Coverage unavailable"}
              />
            )}
          </section>

          <section className="card">
            <div className="card-header">
              <div className="card-title-group">
                <h2 className="card-title">System status</h2>
                <p className="card-subtitle">Live service checks</p>
              </div>
            </div>
            <div className="system-list">
              <div className="system-row">
                <span className="system-label">
                  <DatabaseIcon /> API service
                </span>
                <span
                  className={`badge ${
                    apiOnline ? "badge-success" : "badge-warning"
                  }`}
                >
                  {apiOnline ? "Online" : "Offline"}
                </span>
              </div>
              <div className="system-row">
                <span className="system-label">
                  <DatabaseIcon /> Database
                </span>
                <span
                  className={`badge ${
                    health?.database === "ok" ? "badge-success" : "badge-warning"
                  }`}
                >
                  {health?.database === "ok" ? "Healthy" : "Unknown"}
                </span>
              </div>
              <div className="system-row">
                <span className="system-label">
                  <CrosshairIcon /> Automation
                </span>
                <span className="badge badge-muted">Not scheduled</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
