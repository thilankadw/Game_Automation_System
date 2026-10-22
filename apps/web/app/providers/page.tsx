import Link from "next/link";

import { DeleteButton } from "@/components/delete-button";
import { EmptyState } from "@/components/empty-state";
import {
  ArrowRightIcon,
  ProvidersIcon,
  SearchIcon,
} from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { ProviderFormButton } from "@/components/provider-form-button";
import {
  type Game,
  type GameProvider,
  type Page,
  getAllGames,
  getProvidersPage,
  getRoiSets,
} from "@/lib/api";
import { formatNumber, getInitials } from "@/lib/format";

export const dynamic = "force-dynamic";

interface ProvidersPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

interface ProviderCard {
  provider: GameProvider;
  games: number | null;
  roiSets: number | null;
}

/**
 * Normalize a Next.js search param that may arrive as a repeated value.
 */
function readParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

/**
 * Renders the searchable provider directory with coverage metrics.
 */
export default async function ProvidersPage({
  searchParams,
}: ProvidersPageProps) {
  const params = await searchParams;
  const query = readParam(params.q).trim();

  const [providersResult, gamesResult] = await Promise.allSettled([
    getProvidersPage({ name: query || undefined, limit: 100 }),
    getAllGames(),
  ]);

  const providersPage: Page<GameProvider> | null =
    providersResult.status === "fulfilled" ? providersResult.value : null;
  const games: Game[] | null =
    gamesResult.status === "fulfilled" ? gamesResult.value : null;

  // ROI sets are provider-scoped, so each provider needs its own request.
  // Settled results keep a single failure from hiding the whole directory.
  const roiSetResults = providersPage
    ? await Promise.allSettled(
        providersPage.items.map((provider) => getRoiSets(provider.id)),
      )
    : [];

  const cards: ProviderCard[] =
    providersPage?.items.map((provider, index) => {
      const result = roiSetResults[index];
      return {
        provider,
        games: games
          ? games.filter((game) => game.game_provider_id === provider.id).length
          : null,
        roiSets:
          result && result.status === "fulfilled" ? result.value.length : null,
      };
    }) ?? [];

  return (
    <>
      <PageHeader
        actions={
          <>
            <ProviderFormButton
              triggerClassName="button button-primary"
              triggerLabel="Add provider"
            />
            <span className="status-pill" data-online={providersPage !== null}>
              {providersPage !== null ? "API connected" : "API offline"}
            </span>
          </>
        }
        description="The studios and platforms behind each title, with ROI coverage at a glance."
        eyebrow="Integrations"
        title="Game providers"
      />

      <div className="toolbar">
        <form action="/providers" className="search-form" method="get">
          <div className="search-field">
            <SearchIcon />
            <label className="sr-only" htmlFor="provider-search">
              Search providers
            </label>
            <input
              className="input"
              defaultValue={query}
              id="provider-search"
              name="q"
              placeholder="Search providers…"
              type="search"
            />
          </div>
          <button className="button" type="submit">
            Search
          </button>
          {query ? (
            <Link className="button button-ghost" href="/providers">
              Clear
            </Link>
          ) : null}
        </form>
        {providersPage ? (
          <p className="toolbar-meta">
            {formatNumber(providersPage.total)} provider
            {providersPage.total === 1 ? "" : "s"}
          </p>
        ) : null}
      </div>

      {cards.length > 0 ? (
        <div className="provider-card-grid">
          {cards.map((card) => (
            <article className="provider-card" key={card.provider.id}>
              <Link
                className="provider-card-body"
                href={`/providers/${card.provider.id}`}
              >
                <div className="provider-card-top">
                  <span className="provider-avatar provider-avatar-lg">
                    {getInitials(card.provider.name)}
                  </span>
                  <span className="badge badge-muted">
                    #{card.provider.id}
                  </span>
                </div>
                <h2 className="provider-card-name">{card.provider.name}</h2>
                <p className="provider-card-meta">
                  {card.games !== null
                    ? `${formatNumber(card.games)} games`
                    : "Game data unavailable"}{" "}
                  ·{" "}
                  {card.roiSets !== null
                    ? `${formatNumber(card.roiSets)} ROI sets`
                    : "ROI data unavailable"}
                </p>
                <div className="provider-card-stats">
                  <div className="provider-stat">
                    <p className="provider-stat-value">
                      {card.games !== null ? formatNumber(card.games) : "—"}
                    </p>
                    <p className="provider-stat-label">Games</p>
                  </div>
                  <div className="provider-stat">
                    <p className="provider-stat-value">
                      {card.roiSets !== null ? formatNumber(card.roiSets) : "—"}
                    </p>
                    <p className="provider-stat-label">ROI sets</p>
                  </div>
                </div>
                <span className="provider-card-arrow">
                  Open workspace <ArrowRightIcon />
                </span>
              </Link>
              <div className="provider-card-actions">
                <ProviderFormButton
                  provider={card.provider}
                  triggerClassName="button button-sm"
                  triggerLabel="Edit"
                />
                <DeleteButton
                  id={card.provider.id}
                  kind="provider"
                  name={card.provider.name}
                />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <section className="card">
          <EmptyState
            description={
              providersPage
                ? query
                  ? "Try a different provider name or clear the search."
                  : "Use Add provider to start grouping games and ROI sets."
                : "Start the API server and reload this page to load providers."
            }
            icon={<ProvidersIcon />}
            title={
              providersPage
                ? query
                  ? "No matching providers"
                  : "No providers yet"
                : "Providers unavailable"
            }
          />
        </section>
      )}
    </>
  );
}
