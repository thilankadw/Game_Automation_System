import Link from "next/link";

import { DeleteButton } from "@/components/delete-button";
import { EmptyState } from "@/components/empty-state";
import { GameFormButton } from "@/components/game-form-button";
import {
  ArrowRightIcon,
  DatabaseIcon,
  SearchIcon,
} from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { RoiCaptureButton } from "@/components/roi-capture-button";
import { ScreenshotCaptureButton } from "@/components/screenshot-capture-button";
import {
  API_URL,
  type Game,
  type GameProvider,
  type Page,
  getAllProviders,
  getGamesPage,
} from "@/lib/api";
import { formatNumber, formatUrlHost } from "@/lib/format";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

interface GamesPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
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
 * Build a pagination URL while preserving the active search query.
 */
function pageHref(page: number, query: string): string {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  if (page > 0) {
    params.set("page", String(page));
  }
  const serialized = params.toString();
  return serialized ? `/games?${serialized}` : "/games";
}

/**
 * Renders the searchable, paginated game catalog.
 */
export default async function GamesPage({ searchParams }: GamesPageProps) {
  const params = await searchParams;
  const query = readParam(params.q).trim();
  const requestedPage = Number.parseInt(readParam(params.page), 10);
  const page = Number.isFinite(requestedPage) && requestedPage > 0
    ? requestedPage
    : 0;

  const [gamesResult, providersResult] = await Promise.allSettled([
    getGamesPage({
      name: query || undefined,
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    }),
    getAllProviders(),
  ]);

  const gamesPage: Page<Game> | null =
    gamesResult.status === "fulfilled" ? gamesResult.value : null;
  const providers: GameProvider[] | null =
    providersResult.status === "fulfilled" ? providersResult.value : null;
  const providerNames = new Map(
    (providers ?? []).map((provider) => [provider.id, provider.name]),
  );

  const totalPages = gamesPage
    ? Math.max(1, Math.ceil(gamesPage.total / PAGE_SIZE))
    : 1;
  const currentPage = Math.min(page, totalPages - 1);
  const firstRecord = gamesPage ? gamesPage.skip + 1 : 0;
  const lastRecord = gamesPage
    ? Math.min(gamesPage.skip + gamesPage.items.length, gamesPage.total)
    : 0;

  return (
    <>
      <PageHeader
        actions={
          <>
            <GameFormButton
              providers={providers ?? []}
              triggerLabel="Add game"
              triggerClassName="button button-primary"
            />
            <span className="status-pill" data-online={gamesPage !== null}>
              {gamesPage !== null ? "API connected" : "API offline"}
            </span>
          </>
        }
        description="Every title wired into the automation catalog, with its provider and capture layout."
        eyebrow="Catalog"
        title="Games"
      />

      <section className="card">
        <div className="card-header">
          <div className="card-title-group">
            <h2 className="card-title">
              {query ? `Results for “${query}”` : "All games"}
            </h2>
            <p className="card-subtitle">
              {gamesPage
                ? `${formatNumber(gamesPage.total)} matching games`
                : "Catalog unavailable"}
            </p>
          </div>
          <form action="/games" className="search-form" method="get">
            <div className="search-field">
              <SearchIcon />
              <label className="sr-only" htmlFor="game-search">
                Search games
              </label>
              <input
                className="input"
                defaultValue={query}
                id="game-search"
                name="q"
                placeholder="Search games…"
                type="search"
              />
            </div>
            <button className="button" type="submit">
              Search
            </button>
            {query ? (
              <Link className="button button-ghost" href="/games">
                Clear
              </Link>
            ) : null}
          </form>
        </div>

        {gamesPage && gamesPage.items.length > 0 ? (
          <>
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
                    <th className="table-actions" scope="col">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {gamesPage.items.map((game) => (
                    <tr key={game.id}>
                      <td>
                        <Link
                          className="game-link"
                          href={`/games/${game.id}`}
                        >
                          {game.name}
                          <ArrowRightIcon />
                        </Link>
                        <span className="table-secondary">
                          {formatUrlHost(game.url)}
                        </span>
                      </td>
                      <td>
                        {providerNames.get(game.game_provider_id) ??
                          `Provider #${game.game_provider_id}`}
                      </td>
                      <td className="numeric">
                        {formatNumber(game.number_of_spins)}
                        <span className="table-secondary">
                          {game.spin_wait_seconds}s wait
                        </span>
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
                      <td className="table-actions">
                        <div className="row-actions">
                          <RoiCaptureButton
                            gameId={game.id}
                            gameName={game.name}
                          />
                          <ScreenshotCaptureButton
                            apiBaseUrl={API_URL}
                            gameId={game.id}
                            gameName={game.name}
                          />
                          <GameFormButton
                            game={game}
                            providers={providers ?? []}
                            triggerClassName="button button-sm"
                            triggerLabel="Edit"
                          />
                          <DeleteButton
                            id={game.id}
                            kind="game"
                            name={game.name}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <p className="pagination-info">
                Showing {formatNumber(firstRecord)}–{formatNumber(lastRecord)} of{" "}
                {formatNumber(gamesPage.total)}
              </p>
              <div className="pagination-links">
                <Link
                  aria-disabled={currentPage === 0}
                  className="pagination-link"
                  href={pageHref(currentPage - 1, query)}
                >
                  Previous
                </Link>
                <span className="pagination-link" aria-disabled="true">
                  {currentPage + 1} / {totalPages}
                </span>
                <Link
                  aria-disabled={currentPage >= totalPages - 1}
                  className="pagination-link"
                  href={pageHref(currentPage + 1, query)}
                >
                  Next
                </Link>
              </div>
            </div>
          </>
        ) : (
          <EmptyState
            description={
              gamesPage
                ? query
                  ? "Try a different game name or clear the search."
                  : "Use Add game to create the first entry in the catalog."
                : "Start the API server and reload this page to load the catalog."
            }
            icon={<DatabaseIcon />}
            title={
              gamesPage
                ? query
                  ? "No matching games"
                  : "No games yet"
                : "Catalog unavailable"
            }
          />
        )}
      </section>
    </>
  );
}
