"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition, type FormEvent } from "react";

import { SearchableProviderSelect } from "@/components/searchable-provider-select";
import { createGameAction, updateGameAction } from "@/lib/actions";
import type { Game, GameInput, GameProvider } from "@/lib/api";

export interface GameFormProps {
  providers: GameProvider[];
  game?: Game | null;
  onClose: () => void;
}

/**
 * Create or edit form for a game, including the searchable provider picker.
 */
export function GameForm({ providers, game, onClose }: GameFormProps) {
  const router = useRouter();
  const fieldId = useId();
  const [name, setName] = useState(game?.name ?? "");
  const [url, setUrl] = useState(game?.url ?? "");
  const [numberOfSpins, setNumberOfSpins] = useState(
    String(game?.number_of_spins ?? 1000),
  );
  const [providerId, setProviderId] = useState<number | null>(
    game?.game_provider_id ?? null,
  );
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isPending) {
      return;
    }

    setError(null);

    if (providerId === null) {
      setError("Select a game provider.");
      return;
    }

    const input: GameInput = {
      name,
      url,
      number_of_spins: Number(numberOfSpins),
      game_provider_id: providerId,
    };

    startTransition(async () => {
      const result = game
        ? await updateGameAction(game.id, input)
        : await createGameAction(input);

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
          Game name
        </label>
        <input
          autoFocus
          className="input"
          id={`${fieldId}-name`}
          maxLength={255}
          onChange={(event) => setName(event.target.value)}
          placeholder="Book of Fortune"
          required
          type="text"
          value={name}
        />
      </div>

      <SearchableProviderSelect
        hint="Type to filter providers by name."
        initialProviders={providers}
        label="Game provider"
        onChange={(provider) => setProviderId(provider?.id ?? null)}
        value={providerId}
      />

      <div className="form-field">
        <label className="form-label" htmlFor={`${fieldId}-url`}>
          Game URL
        </label>
        <input
          className="input"
          id={`${fieldId}-url`}
          maxLength={2048}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://provider.example/game"
          required
          type="url"
          value={url}
        />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor={`${fieldId}-spins`}>
          Number of spins
        </label>
        <input
          className="input"
          id={`${fieldId}-spins`}
          min={0}
          onChange={(event) => setNumberOfSpins(event.target.value)}
          required
          step={1}
          type="number"
          value={numberOfSpins}
        />
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
          {isPending ? "Saving…" : game ? "Save changes" : "Create game"}
        </button>
      </div>
    </form>
  );
}
