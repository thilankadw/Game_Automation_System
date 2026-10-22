"use client";

import { useState, useTransition } from "react";

import { Modal } from "@/components/modal";
import { startRoiCaptureAction } from "@/lib/actions";

export interface RoiCaptureButtonProps {
  gameId: number;
  gameName: string;
  triggerClassName?: string;
}

/**
 * Starts a live Chrome session and explains how to draw ROIs in the overlay.
 *
 * The drawing itself happens in the browser window opened by the backend, so
 * this control only reports success or the API error in a dialog.
 */
export function RoiCaptureButton({
  gameId,
  gameName,
  triggerClassName = "button button-sm",
}: RoiCaptureButtonProps) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [isPending, startTransition] = useTransition();

  const start = () => {
    setError(null);
    setStarted(false);
    startTransition(async () => {
      const result = await startRoiCaptureAction(gameId);

      if (!result.ok) {
        setError(result.error);
        setOpen(true);
        return;
      }

      setStarted(true);
      setOpen(true);
    });
  };

  const close = () => {
    setOpen(false);
    setError(null);
  };

  return (
    <>
      <button
        className={triggerClassName}
        disabled={isPending}
        onClick={start}
        type="button"
      >
        {isPending ? "Opening…" : "Draw ROIs"}
      </button>
      {open ? (
        <Modal
          description={
            started
              ? "Mark the canvas, spin button, balance, bet, and win regions in the game window."
              : "The backend could not open the game in Chrome."
          }
          onClose={close}
          title={started ? "Chrome window opened" : "ROI capture failed"}
        >
          <div className="modal-form">
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            {started ? (
              <p className="confirm-copy">
                <strong>{gameName}</strong> is open in a new Chrome window.
                Play spins in the <em>Play spins</em> mode, switch to{" "}
                <em>Draw ROI</em>, pick a region, and drag over the game. Choose
                the ROI set and press <em>Save ROIs</em> in the overlay.
              </p>
            ) : null}
            <div className="form-actions">
              <button
                className="button button-ghost"
                onClick={close}
                type="button"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
