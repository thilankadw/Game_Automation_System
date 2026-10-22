"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition, type FormEvent } from "react";

import { createRoiSetAction, updateRoiSetAction } from "@/lib/actions";
import type { RoiInput, RoiName, RoiSet, RoiSetInput } from "@/lib/api";

export interface RoiSetFormProps {
  providerId: number;
  roiSet?: RoiSet | null;
  onClose: () => void;
}

interface RegionDraft {
  x: string;
  y: string;
  width: string;
  height: string;
}

interface RegionDefinition {
  name: RoiName;
  label: string;
}

const REGIONS: readonly RegionDefinition[] = [
  { name: "canvas", label: "Canvas" },
  { name: "spin_button", label: "Spin button" },
  { name: "balance", label: "Balance" },
  { name: "bet", label: "Bet" },
  { name: "win", label: "Win" },
];

const EMPTY_DRAFT: RegionDraft = { x: "", y: "", width: "", height: "" };

/** Coordinates entered out of order are still accepted as whole numbers. */
function parseCoordinate(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) ? parsed : null;
}

/**
 * Create or edit form for a provider's ROI set.
 *
 * Regions can be typed by hand or captured later with the Draw ROIs tool.
 * Leaving all four fields of a region blank omits that region from the set.
 */
export function RoiSetForm({ providerId, roiSet, onClose }: RoiSetFormProps) {
  const router = useRouter();
  const fieldId = useId();
  const [name, setName] = useState(roiSet?.name ?? "");
  const [drafts, setDrafts] = useState<Record<RoiName, RegionDraft>>(() => {
    const initial = Object.fromEntries(
      REGIONS.map((region) => [region.name, { ...EMPTY_DRAFT }]),
    ) as Record<RoiName, RegionDraft>;

    for (const roi of roiSet?.rois ?? []) {
      if (roi.name in initial) {
        initial[roi.name as RoiName] = {
          x: String(roi.x),
          y: String(roi.y),
          width: String(roi.width),
          height: String(roi.height),
        };
      }
    }

    return initial;
  });
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const isEditing = Boolean(roiSet);

  const setDraftValue = (
    region: RoiName,
    field: keyof RegionDraft,
    value: string,
  ) => {
    setDrafts((current) => ({
      ...current,
      [region]: { ...current[region], [field]: value },
    }));
  };

  const clearRegion = (region: RoiName) => {
    setDrafts((current) => ({ ...current, [region]: { ...EMPTY_DRAFT } }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isPending) {
      return;
    }

    setError(null);

    const trimmedName = name.trim();
    if (isEditing && !trimmedName) {
      setError("ROI set name is required.");
      return;
    }

    const rois: RoiInput[] = [];

    for (const region of REGIONS) {
      const draft = drafts[region.name];
      const values = [draft.x, draft.y, draft.width, draft.height];
      const isBlank = values.every((value) => value.trim() === "");

      if (isBlank) {
        continue;
      }

      if (values.some((value) => value.trim() === "")) {
        setError(`Fill in all four fields for ${region.label}, or clear them.`);
        return;
      }

      const x = parseCoordinate(draft.x);
      const y = parseCoordinate(draft.y);
      const width = parseCoordinate(draft.width);
      const height = parseCoordinate(draft.height);

      if (x === null || y === null || width === null || height === null) {
        setError(`${region.label} coordinates must be whole numbers.`);
        return;
      }
      if (x < 0 || y < 0) {
        setError(`${region.label} X and Y must be 0 or greater.`);
        return;
      }
      if (width <= 0 || height <= 0) {
        setError(`${region.label} width and height must be above 0.`);
        return;
      }

      rois.push({ name: region.name, x, y, width, height });
    }

    const input: RoiSetInput = {
      rois,
      ...(trimmedName ? { name: trimmedName } : {}),
    };

    startTransition(async () => {
      const result = roiSet
        ? await updateRoiSetAction(roiSet.id, input)
        : await createRoiSetAction(providerId, input);

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
          ROI set name
        </label>
        <input
          autoFocus
          className="input"
          id={`${fieldId}-name`}
          maxLength={255}
          onChange={(event) => setName(event.target.value)}
          placeholder={isEditing ? "Option 1" : "Leave blank for Option N"}
          required={isEditing}
          type="text"
          value={name}
        />
      </div>

      <div className="form-field">
        <span className="form-label">Regions</span>
        <p className="form-hint">
          Enter pixel offsets for a region, or leave it blank and use Draw ROIs
          on the Games page to capture it from the live game.
        </p>
      </div>

      <div className="roi-form-list">
        {REGIONS.map((region) => {
          const draft = drafts[region.name];
          const isFilled = Object.values(draft).some(
            (value) => value.trim() !== "",
          );

          return (
            <fieldset className="roi-form-region" key={region.name}>
              <legend className="roi-form-legend">{region.label}</legend>
              <div className="roi-form-inputs">
                {(
                  [
                    ["x", "X", 0],
                    ["y", "Y", 0],
                    ["width", "Width", 1],
                    ["height", "Height", 1],
                  ] as const
                ).map(([field, label, min]) => (
                  <label className="roi-form-input" key={field}>
                    <span>{label}</span>
                    <input
                      aria-label={`${region.label} ${label}`}
                      className="input"
                      inputMode="numeric"
                      min={min}
                      onChange={(event) =>
                        setDraftValue(region.name, field, event.target.value)
                      }
                      placeholder="—"
                      step={1}
                      type="number"
                      value={draft[field]}
                    />
                  </label>
                ))}
                <button
                  className="button button-ghost button-sm roi-form-clear"
                  disabled={!isFilled || isPending}
                  onClick={() => clearRegion(region.name)}
                  type="button"
                >
                  Clear
                </button>
              </div>
            </fieldset>
          );
        })}
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
            : isEditing
              ? "Save changes"
              : "Create ROI set"}
        </button>
      </div>
    </form>
  );
}
