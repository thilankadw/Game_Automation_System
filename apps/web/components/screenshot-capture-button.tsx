"use client";

import { useEffect, useState, useTransition } from "react";

import { Modal } from "@/components/modal";
import {
  getScreenshotCaptureSessionAction,
  startScreenshotCaptureAction,
  stopScreenshotCaptureAction,
} from "@/lib/actions";
import type { ScreenshotCaptureSession } from "@/lib/api";

export interface ScreenshotCaptureButtonProps {
  gameId: number;
  gameName: string;
  apiBaseUrl: string;
  triggerClassName?: string;
}

const ACTIVE_STATUSES = new Set(["starting", "running"]);
const POLL_INTERVAL_MS = 2000;

/** Human-readable summary for the current session status. */
function statusCopy(session: ScreenshotCaptureSession): string {
  switch (session.status) {
    case "starting":
      return "Starting Chrome and loading the game…";
    case "running": {
      const spin = Math.min(
        session.completed_spins + 1,
        session.total_spins,
      );
      return `Capturing spin ${spin} of ${session.total_spins}…`;
    }
    case "completed":
      return `Finished ${session.completed_spins} of ${session.total_spins} spins.`;
    case "cancelled":
      return `Stopped after ${session.completed_spins} of ${session.total_spins} spins.`;
    case "failed":
      return "The capture stopped because of an error.";
    default:
      return "Capture status unavailable.";
  }
}

/**
 * Starts an automated screenshot run and polls the backend for progress.
 *
 * The capture itself happens in a headed Chrome window on the backend, so this
 * control reports progress and lets the operator stop the run.
 */
export function ScreenshotCaptureButton({
  gameId,
  gameName,
  apiBaseUrl,
  triggerClassName = "button button-sm",
}: ScreenshotCaptureButtonProps) {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState<ScreenshotCaptureSession | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [isStarting, startTransition] = useTransition();
  const [isStopping, startStopTransition] = useTransition();

  const isActive = session ? ACTIVE_STATUSES.has(session.status) : false;

  useEffect(() => {
    if (!open || !session || !ACTIVE_STATUSES.has(session.status)) {
      return;
    }

    const sessionId = session.id;
    let cancelled = false;
    const interval = window.setInterval(async () => {
      const result = await getScreenshotCaptureSessionAction(sessionId);
      if (cancelled) {
        return;
      }
      if (!result.ok) {
        setError(result.error);
        return;
      }
      setError(null);
      setSession(result.session);
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [open, session]);

  const start = () => {
    setError(null);
    setSession(null);
    startTransition(async () => {
      const result = await startScreenshotCaptureAction(gameId);

      if (!result.ok) {
        setError(result.error);
        setOpen(true);
        return;
      }

      setSession(result.session);
      setOpen(true);
    });
  };

  const handleTrigger = () => {
    if (isActive) {
      setOpen(true);
      return;
    }
    start();
  };

  const stop = () => {
    if (!session) {
      return;
    }

    setError(null);
    startStopTransition(async () => {
      const result = await stopScreenshotCaptureAction(session.id);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      const refreshed = await getScreenshotCaptureSessionAction(session.id);
      if (refreshed.ok) {
        setSession(refreshed.session);
      }
    });
  };

  const close = () => {
    setOpen(false);
    setError(null);
  };

  const progress = session
    ? Math.min(
        100,
        Math.round(
          (session.completed_spins / Math.max(1, session.total_spins)) * 100,
        ),
      )
    : 0;

  return (
    <>
      <button
        className={triggerClassName}
        disabled={isStarting}
        onClick={handleTrigger}
        type="button"
      >
        {isStarting ? "Starting…" : "Capture"}
      </button>
      {open ? (
        <Modal
          description={
            session
              ? `${gameName} · ROI set ${session.roi_set_name}`
              : `${gameName} could not start a screenshot run.`
          }
          onClose={close}
          title={session ? "Spin capture" : "Screenshot capture failed"}
        >
          <div className="modal-form">
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}

            {session ? (
              <>
                <div className="capture-status" aria-live="polite">
                  <p className="confirm-copy">
                    <strong>{statusCopy(session)}</strong>
                  </p>
                  <div
                    aria-valuemax={session.total_spins}
                    aria-valuemin={0}
                    aria-valuenow={session.completed_spins}
                    className="capture-progress"
                    role="progressbar"
                  >
                    <span
                      className="capture-progress-bar"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="capture-meta">
                    {session.completed_spins} / {session.total_spins} spins ·{" "}
                    {session.spin_wait_seconds}s wait
                  </p>
                </div>

                {session.error ? (
                  <p className="form-error" role="alert">
                    {session.error}
                  </p>
                ) : null}

                {session.latest_screenshot ? (
                  <figure className="capture-preview">
                    {/* The API serves captured PNGs from the /screenshots mount. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      alt={`Latest capture for ${session.game_name}`}
                      src={`${apiBaseUrl}${session.latest_screenshot}`}
                    />
                    <figcaption>
                      Latest screenshot · spin {session.completed_spins}
                    </figcaption>
                  </figure>
                ) : null}

                <p className="capture-output">
                  Saved to <code>{session.output_path}</code>
                </p>
              </>
            ) : null}

            <div className="form-actions">
              <button
                className="button button-ghost"
                onClick={close}
                type="button"
              >
                Close
              </button>
              {session && isActive ? (
                <button
                  className="button button-danger"
                  disabled={isStopping}
                  onClick={stop}
                  type="button"
                >
                  {isStopping ? "Stopping…" : "Stop capture"}
                </button>
              ) : null}
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
