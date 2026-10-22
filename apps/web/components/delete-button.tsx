"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Modal } from "@/components/modal";
import {
  deleteGameAction,
  deleteProviderAction,
  deleteRoiSetAction,
} from "@/lib/actions";

export interface DeleteButtonProps {
  kind: "game" | "provider" | "roi-set";
  id: number;
  name: string;
  triggerClassName?: string;
}

const kindLabels: Record<DeleteButtonProps["kind"], string> = {
  game: "game",
  provider: "provider",
  "roi-set": "ROI set",
};

const confirmCopy: Record<DeleteButtonProps["kind"], string> = {
  game: "Its catalog entry and automation settings will be removed.",
  provider:
    "Its ROI sets are removed with it, and games assigned to it are left without a provider.",
  "roi-set":
    "Games using it will stop having saved coordinates until another set is assigned.",
};

/**
 * Two-step delete control with a confirmation dialog and inline API errors.
 */
export function DeleteButton({
  kind,
  id,
  name,
  triggerClassName = "button button-sm button-danger",
}: DeleteButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const label = kindLabels[kind];

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
      const result =
        kind === "game"
          ? await deleteGameAction(id)
          : kind === "provider"
            ? await deleteProviderAction(id)
            : await deleteRoiSetAction(id);

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
        className={triggerClassName}
        onClick={() => setOpen(true)}
        type="button"
      >
        Delete
      </button>
      {open ? (
        <Modal
          description={`This action cannot be undone. The ${label} and its API record will be removed.`}
          onClose={close}
          title={`Delete ${label}?`}
        >
          <div className="modal-form">
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            <p className="confirm-copy">
              Delete <strong>{name}</strong>? {confirmCopy[kind]}
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
                {isPending ? "Deleting…" : `Delete ${label}`}
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
