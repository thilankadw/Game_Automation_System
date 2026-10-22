"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition, type FormEvent } from "react";

import { createProviderAction, updateProviderAction } from "@/lib/actions";
import type { GameProvider } from "@/lib/api";

export interface ProviderFormProps {
  provider?: GameProvider | null;
  onClose: () => void;
}

/**
 * Create or edit form for a game provider.
 */
export function ProviderForm({ provider, onClose }: ProviderFormProps) {
  const router = useRouter();
  const fieldId = useId();
  const [name, setName] = useState(provider?.name ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isPending) {
      return;
    }

    setError(null);

    startTransition(async () => {
      const result = provider
        ? await updateProviderAction(provider.id, { name })
        : await createProviderAction({ name });

      if (!result.ok) {
        setError(result.error);
        return;
      }

      router.refresh();
      onClose();
    });
  };

  return (
    <form className="modal-form" onSubmit={handleSubmit}>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="form-field">
        <label className="form-label" htmlFor={`${fieldId}-name`}>
          Provider name
        </label>
        <input
          autoFocus
          className="input"
          id={`${fieldId}-name`}
          maxLength={255}
          onChange={(event) => setName(event.target.value)}
          placeholder="Acme Gaming"
          required
          type="text"
          value={name}
        />
        <p className="form-hint">
          Provider names group games and their ROI sets.
        </p>
      </div>

      <div className="form-actions">
        <button
          className="button button-ghost"
          disabled={isPending}
          onClick={onClose}
          type="button"
        >
          Cancel
        </button>
        <button className="button button-primary" disabled={isPending} type="submit">
          {isPending
            ? "Saving…"
            : provider
              ? "Save changes"
              : "Create provider"}
        </button>
      </div>
    </form>
  );
}
