import { EmptyState } from "@/components/empty-state";
import { DatabaseIcon } from "@/components/icons";
import { OcrReadingsDeleteButton } from "@/components/ocr-readings-delete-button";
import type { OcrSpinReading } from "@/lib/api";
import { formatAmount, formatNumber } from "@/lib/format";

export interface OcrReadingsProps {
  apiBaseUrl: string;
  gameId: number;
  gameName: string;
  readings: OcrSpinReading[];
  total: number;
  unavailable?: boolean;
}

/**
 * Renders the latest stored balance, bet, and win readings for a game.
 *
 * Full history stays in the API; this table shows a capped recent sample so
 * sessions with thousands of spins do not create an enormous page.
 */
export function OcrReadings({
  apiBaseUrl,
  gameId,
  gameName,
  readings,
  total,
  unavailable = false,
}: OcrReadingsProps) {
  return (
    <section className="card">
      <div className="card-header">
        <div className="card-title-group">
          <h2 className="card-title">Extracted spin data</h2>
          <p className="card-subtitle">
            Balance, bet, and win values stored from OCR runs.
          </p>
        </div>
        <div className="card-header-actions">
          <span
            className={
              total > 0 ? "badge badge-accent" : "badge badge-muted"
            }
          >
            {unavailable
              ? "Unavailable"
              : `${formatNumber(total)} ${total === 1 ? "reading" : "readings"}`}
          </span>
          {!unavailable && total > 0 ? (
            <OcrReadingsDeleteButton
              gameId={gameId}
              gameName={gameName}
              readingCount={total}
            />
          ) : null}
        </div>
      </div>

      {unavailable ? (
        <div className="card-body">
          <div className="error-panel">
            <div>
              <p className="error-panel-title">OCR data unavailable</p>
              <p className="error-panel-text">
                Start the API server and reload this page to load stored
                values.
              </p>
            </div>
          </div>
        </div>
      ) : readings.length > 0 ? (
        <>
          <div className="table-wrap">
            <table className="data-table ocr-table">
              <thead>
                <tr>
                  <th scope="col">Spin</th>
                  <th className="numeric" scope="col">
                    Balance
                  </th>
                  <th className="numeric" scope="col">
                    Bet
                  </th>
                  <th className="numeric" scope="col">
                    Win
                  </th>
                  <th scope="col">Session</th>
                  <th scope="col">Frame</th>
                </tr>
              </thead>
              <tbody>
                {readings.map((reading) => (
                  <tr key={reading.id}>
                    <td className="numeric table-primary">
                      {formatNumber(reading.spin_number)}
                    </td>
                    <td
                      className="numeric"
                      title={reading.balance_text ?? undefined}
                    >
                      {formatAmount(reading.balance)}
                    </td>
                    <td
                      className="numeric"
                      title={reading.bet_text ?? undefined}
                    >
                      {formatAmount(reading.bet)}
                    </td>
                    <td
                      className="numeric"
                      title={reading.win_text ?? undefined}
                    >
                      {formatAmount(reading.win)}
                    </td>
                    <td>
                      <span className="ocr-session">
                        {reading.session_id.slice(0, 8)}
                      </span>
                    </td>
                    <td>
                      <a
                        className="ocr-frame-link"
                        href={`${apiBaseUrl}${reading.screenshot_path}`}
                        rel="noreferrer"
                        target="_blank"
                      >
                        Open
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="ocr-readings-footer">
            <p>
              Showing the latest {formatNumber(readings.length)} of{" "}
              {formatNumber(total)} readings.
            </p>
          </div>
        </>
      ) : (
        <div className="card-body">
          <EmptyState
            description="Select a screenshot session from the library and run OCR to store balance, bet, and win values."
            icon={<DatabaseIcon />}
            title="No OCR readings yet"
          />
        </div>
      )}
    </section>
  );
}
