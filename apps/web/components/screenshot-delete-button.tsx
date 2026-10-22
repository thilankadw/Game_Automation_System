"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Modal } from "@/components/modal";
import {
  deleteAllScreenshotsAction,
  deleteScreenshotSessionAction,
} from "@/lib/actions";
import { formatNumber } from "@/lib/format";

/** Format a count with a singular or plural noun. */
function countLabel(count: number, noun: string): string {
  return `${formatNumber(count)} ${noun}${count === 1 ? "" : "s"}`;
}

export interface ScreenshotDeleteButtonProps {
  gameId: number;
  gameName: string;
  frameCount: number;
  sessionId?: string;
  sessionCount?: number;
  triggerClassName?: string;
}

/**
 * Confirms and deletes one stored screenshot session or every session.
 *
 * The confirmation dialog reports the number of affected sessions and frames
 * so a bulk delete is never a one-click action.
 */
export function ScreenshotDeleteButton({
  gameId,
  gameName,
  frameCount,
  sessionId,
  sessionCount = 0,
  triggerClassName = "button button-sm button-danger",
}: ScreenshotDeleteButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const isSession = Boolean(sessionId);
  const sessionLabel = sessionId?.slice(0, 8);
  const triggerLabel = isSession ? "Delete session" : "Delete all screenshots";
  const description = isSession
    ? `Session ${sessionLabel} · ${countLabel(frameCount, "screenshot")}.`
    : `${countLabel(sessionCount, "session")} · ${countLabel(frameCount, "screenshot")} for ${gameName}.`;

  const close = () => {
    if (isPending) {
      return;
    }
    setOpen(false);
    setError(null);
  };

  const confirmDelete = () => {
    setError(null);
    startTransition(async () => {
      const result = sessionId
        ? await deleteScreenshotSessionAction(gameId, sessionId)
        : await deleteAllScreenshotsAction(gameId);

      if (!result.ok) {
        setError(result.error);
        return;
      }

      setOpen(false);
      router.refresh();
    });
  };

  return (
    <>
      <button
        aria-label={
          isSession ? `Delete session ${sessionLabel}` : triggerLabel
        }
        className={triggerClassName}
        onClick={() => setOpen(true)}
        type="button"
      >
        {triggerLabel}
      </button>
      {open ? (
        <Modal
          description={`${description} This action cannot be undone.`}
          onClose={close}
          title={
            isSession
              ? "Delete screenshot session?"
              : "Delete all screenshots?"
          }
        >
          <div className="modal-form">
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            <p className="confirm-copy">
              {isSession ? (
                <>
                  Delete session <strong>{sessionLabel}</strong> and all of
                  its screenshots from disk?
                </>
              ) : (
                <>
                  Delete every saved screenshot for{" "}
                  <strong>{gameName}</strong> from disk?
                </>
              )}
            </p>
            <div className="form-actions">
              <button
                className="button button-ghost"
                disabled={isPending}
                onClick={close}
                type="button"
              >
                Cancel
              </button>
              <button
                className="button button-danger"
                disabled={isPending}
                onClick={confirmDelete}
                type="button"
              >
                {isPending ? "Deleting…" : triggerLabel}
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
