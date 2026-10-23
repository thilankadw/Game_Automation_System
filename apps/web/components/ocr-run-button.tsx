"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { Modal } from "@/components/modal";
import {
  getOcrRunAction,
  startOcrRunAction,
  stopOcrRunAction,
} from "@/lib/actions";
import type { OcrRun, StoredScreenshotSession } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";

export interface OcrRunButtonProps {
  gameId: number;
  gameName: string;
  sessions: StoredScreenshotSession[];
  triggerClassName?: string;
}

const ACTIVE_STATUSES = new Set(["starting", "running"]);
const POLL_INTERVAL_MS = 1000;

/** Human-readable summary for the current OCR status. */
function statusCopy(run: OcrRun): string {
  switch (run.status) {
    case "starting":
      return "Starting the OCR engine...";
    case "running": {
      const spin = Math.min(run.processed_spins + 1, run.total_spins);
      return `Reading spin ${spin} of ${run.total_spins}...`;
    }
    case "completed":
      return `Read ${formatNumber(run.recognized_spins)} of ${formatNumber(
        run.total_spins,
      )} spins.`;
    case "cancelled":
      return `Stopped after ${formatNumber(
        run.processed_spins,
      )} of ${formatNumber(run.total_spins)} spins.`;
    case "failed":
      return "The OCR extraction stopped because of an error.";
    default:
      return "OCR status unavailable.";
  }
}

/**
 * Starts an OCR run for a selected stored screenshot session.
 *
 * The operator chooses which capture session to read, then watches the
 * background run until balance, bet, and win values are stored.
 */
export function OcrRunButton({
  gameId,
  gameName,
  sessions,
  triggerClassName = "button button-sm",
}: OcrRunButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(
    sessions[0]?.id ?? "",
  );
  const [run, setRun] = useState<OcrRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, startTransition] = useTransition();
  const [isStopping, startStopTransition] = useTransition();

  const isActive = run ? ACTIVE_STATUSES.has(run.status) : false;
  const selectedSession =
    sessions.find((session) => session.id === selectedSessionId) ?? null;

  useEffect(() => {
    if (!open || !run || !ACTIVE_STATUSES.has(run.status)) {
      return;
    }

    const runId = run.id;
    let cancelled = false;
    const interval = window.setInterval(async () => {
      const result = await getOcrRunAction(gameId, runId);
      if (cancelled) {
        return;
      }
      if (!result.ok) {
        setError(result.error);
        return;
      }
      setError(null);
      setRun(result.run);
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [gameId, open, run]);

  useEffect(() => {
    if (
      run?.status === "completed" ||
      run?.status === "failed" ||
      run?.status === "cancelled"
    ) {
      router.refresh();
    }
  }, [router, run]);

  const openDialog = () => {
    setError(null);
    if (!isActive) {
      setRun(null);
      setSelectedSessionId(sessions[0]?.id ?? "");
    }
    setOpen(true);
  };

  const start = () => {
    setError(null);
    startTransition(async () => {
      const result = await startOcrRunAction(gameId, selectedSessionId);

      if (!result.ok) {
        setError(result.error);
        return;
      }

      setRun(result.run);
      setOpen(true);
    });
  };

  const stop = () => {
    if (!run) {
      return;
    }

    setError(null);
    startStopTransition(async () => {
      const result = await stopOcrRunAction(gameId, run.id);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      const refreshed = await getOcrRunAction(gameId, run.id);
      if (refreshed.ok) {
        setRun(refreshed.run);
      }
    });
  };

  const close = () => {
    setOpen(false);
    setError(null);
    if (!isActive) {
      setRun(null);
    }
  };

  const progress = run
    ? Math.min(
        100,
        Math.round(
          (run.processed_spins / Math.max(1, run.total_spins)) * 100,
        ),
      )
    : 0;

  return (
    <>
      <button
        className={triggerClassName}
        disabled={isStarting}
        onClick={openDialog}
        type="button"
      >
        {isStarting ? "Starting..." : "Run OCR"}
      </button>
      {open ? (
        <Modal
          description={
            run
              ? `${gameName} - session ${run.session_id.slice(0, 8)}`
              : "Read balance, bet, and win from a stored screenshot session."
          }
          onClose={close}
          title={run ? "OCR extraction" : "Run OCR"}
        >
          <div className="modal-form">
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}

            {run ? (
              <>
                <div className="capture-status" aria-live="polite">
                  <p className="confirm-copy">
                    <strong>{statusCopy(run)}</strong>
                  </p>
                  <div
                    aria-valuemax={run.total_spins}
                    aria-valuemin={0}
                    aria-valuenow={run.processed_spins}
                    className="capture-progress"
                    role="progressbar"
                  >
                    <span
                      className="capture-progress-bar"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="capture-meta">
                    {formatNumber(run.processed_spins)} /{" "}
                    {formatNumber(run.total_spins)} frames -{" "}
                    {formatNumber(run.recognized_spins)} recognized
                  </p>
                </div>

                {run.error ? (
                  <p className="form-error" role="alert">
                    {run.error}
                  </p>
                ) : null}

                {run.status === "completed" ? (
                  <p className="form-hint">
                    Stored readings are available in the extracted spin data
                    table.
                  </p>
                ) : null}
              </>
            ) : (
              <>
                <div className="form-field">
                  <label className="form-label" htmlFor="ocr-session">
                    Screenshot session
                  </label>
                  <select
                    className="input"
                    disabled={sessions.length === 0}
                    id="ocr-session"
                    onChange={(event) =>
                      setSelectedSessionId(event.target.value)
                    }
                    value={selectedSessionId}
                  >
                    {sessions.map((session) => (
                      <option key={session.id} value={session.id}>
                        Session {session.id.slice(0, 8)} -{" "}
                        {formatNumber(session.screenshot_count)} frames -{" "}
                        {formatDateTime(session.created_at)}
                      </option>
                    ))}
                  </select>
                  {selectedSession ? (
                    <p className="form-hint">
                      {selectedSession.width}x{selectedSession.height} -{" "}
                      {formatNumber(selectedSession.screenshot_count)} frames
                    </p>
                  ) : (
                    <p className="form-hint">
                      Capture a screenshot session before running OCR.
                    </p>
                  )}
                </div>
                <p className="form-hint">
                  Balance, bet, and win are read from this game&apos;s ROI set.
                </p>
              </>
            )}

            <div className="form-actions">
              <button
                className="button button-ghost"
                onClick={close}
                type="button"
              >
                Close
              </button>
              {run ? (
                isActive ? (
                  <button
                    className="button button-danger"
                    disabled={isStopping}
                    onClick={stop}
                    type="button"
                  >
                    {isStopping ? "Stopping..." : "Stop OCR"}
                  </button>
                ) : null
              ) : (
                <button
                  className="button button-primary"
                  disabled={!selectedSessionId || isStarting}
                  onClick={start}
                  type="button"
                >
                  {isStarting ? "Starting..." : "Start OCR"}
                </button>
              )}
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
