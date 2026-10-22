"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useId,
  useState,
  useTransition,
  type FormEvent,
} from "react";

import { SearchableProviderSelect } from "@/components/searchable-provider-select";
import {
  createGameAction,
  getRoiSetsAction,
  updateGameAction,
} from "@/lib/actions";
import type { Game, GameInput, GameProvider, RoiSet } from "@/lib/api";

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
  const [spinWaitSeconds, setSpinWaitSeconds] = useState(
    String(game?.spin_wait_seconds ?? 12),
  );
  const [providerId, setProviderId] = useState<number | null>(
    game?.game_provider_id ?? null,
  );
  const [roiSetId, setRoiSetId] = useState<number | null>(
    game?.roi_set_id ?? null,
  );
  const [roiSets, setRoiSets] = useState<RoiSet[]>(
    game?.roi_set ? [game.roi_set] : [],
  );
  const [isLoadingRoiSets, setIsLoadingRoiSets] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (providerId === null) {
      setRoiSets([]);
      setRoiSetId(null);
      setIsLoadingRoiSets(false);
      return;
    }

    let cancelled = false;
    setIsLoadingRoiSets(true);

    void getRoiSetsAction(providerId).then((result) => {
      if (cancelled) {
        return;
      }

      setIsLoadingRoiSets(false);

      if (!result.ok) {
        setError(result.error);
        return;
      }

      setRoiSets(result.roiSets);
      // Drop a selection that belongs to a different provider.
      setRoiSetId((current) =>
        current !== null &&
        result.roiSets.some((roiSet) => roiSet.id === current)
          ? current
          : null,
      );
    });

    return () => {
      cancelled = true;
    };
  }, [providerId]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isPending || isLoadingRoiSets) {
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
      spin_wait_seconds: Number(spinWaitSeconds),
      game_provider_id: providerId,
      roi_set_id: roiSetId,
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
        <label className="form-label" htmlFor={`${fieldId}-roi-set`}>
          ROI set
        </label>
        <select
          className="input"
          disabled={providerId === null || isLoadingRoiSets}
          id={`${fieldId}-roi-set`}
          onChange={(event) =>
            setRoiSetId(
              event.target.value ? Number(event.target.value) : null,
            )
          }
          value={roiSetId === null ? "" : String(roiSetId)}
        >
          <option value="">
            {providerId === null ? "Select a provider first" : "No ROI set"}
          </option>
          {roiSets.map((roiSet) => (
            <option key={roiSet.id} value={roiSet.id}>
              {roiSet.name} · {roiSet.rois.length} region
              {roiSet.rois.length === 1 ? "" : "s"}
            </option>
          ))}
        </select>
        <p className="form-hint">
          {providerId === null ? (
            "Choose a provider to load its ROI sets."
          ) : isLoadingRoiSets ? (
            "Loading ROI sets…"
          ) : roiSets.length === 0 ? (
            <>
              No ROI sets for this provider.{" "}
              <Link href={`/providers/${providerId}`}>
                Create one on the provider page
              </Link>
              .
            </>
          ) : (
            "The spin button is required; other regions are optional."
          )}
        </p>
      </div>

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

      <div className="form-field">
        <label className="form-label" htmlFor={`${fieldId}-wait`}>
          Spin wait (seconds)
        </label>
        <input
          className="input"
          id={`${fieldId}-wait`}
          min={0}
          onChange={(event) => setSpinWaitSeconds(event.target.value)}
          required
          step={1}
          type="number"
          value={spinWaitSeconds}
        />
        <p className="form-hint">
          Time to wait after each spin before the screenshot is captured.
          Defaults to 12 seconds.
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
        <button
          className="button button-primary"
          disabled={isPending || isLoadingRoiSets}
          type="submit"
        >
          {isPending ? "Saving…" : game ? "Save changes" : "Create game"}
        </button>
      </div>
    </form>
  );
}
