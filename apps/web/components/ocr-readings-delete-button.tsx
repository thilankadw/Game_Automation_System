"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Modal } from "@/components/modal";
import {
  deleteAllOcrReadingsAction,
  deleteOcrSessionReadingsAction,
} from "@/lib/actions";
import { formatNumber } from "@/lib/format";

function readingLabel(count: number): string {
  return `${formatNumber(count)} ${count === 1 ? "reading" : "readings"}`;
}

export interface OcrReadingsDeleteButtonProps {
  gameId: number;
  gameName: string;
  readingCount: number;
  sessionId?: string;
  triggerClassName?: string;
}

/**
 * Confirms and deletes OCR readings for one session or for the whole game.
 *
 * Bulk deletion always goes through a confirmation dialog that reports how
 * many stored readings will be removed.
 */
export function OcrReadingsDeleteButton({
  gameId,
  gameName,
  readingCount,
  sessionId,
  triggerClassName = "button button-sm button-danger",
}: OcrReadingsDeleteButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const isSession = Boolean(sessionId);
  const sessionLabel = sessionId?.slice(0, 8);
  const triggerLabel = isSession
    ? "Delete OCR data"
    : "Delete all OCR data";
  const description = isSession
    ? `${readingLabel(readingCount)} from session ${sessionLabel}.`
    : `${readingLabel(readingCount)} for ${gameName}.`;

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
        ? await deleteOcrSessionReadingsAction(gameId, sessionId)
        : await deleteAllOcrReadingsAction(gameId);

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
          isSession
            ? `Delete OCR data for session ${sessionLabel}`
            : triggerLabel
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
          title="Delete OCR readings?"
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
                  Delete every OCR reading extracted from session{" "}
                  <strong>{sessionLabel}</strong>?
                </>
              ) : (
                <>
                  Delete every OCR reading stored for{" "}
                  <strong>{gameName}</strong>?
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
                {isPending ? "Deleting..." : triggerLabel}
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
