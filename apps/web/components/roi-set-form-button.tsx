"use client";

import { useState } from "react";

import { PlusIcon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { RoiSetForm } from "@/components/roi-set-form";
import type { RoiSet } from "@/lib/api";

export interface RoiSetFormButtonProps {
  providerId: number;
  roiSet?: RoiSet | null;
  triggerLabel: string;
  triggerClassName?: string;
}

/**
 * Trigger button that opens the create or edit ROI set dialog.
 */
export function RoiSetFormButton({
  providerId,
  roiSet,
  triggerLabel,
  triggerClassName = "button button-primary",
}: RoiSetFormButtonProps) {
  const [open, setOpen] = useState(false);
  const isEditing = Boolean(roiSet);

  return (
    <>
      <button
        className={triggerClassName}
        onClick={() => setOpen(true)}
        type="button"
      >
        {!isEditing ? <PlusIcon /> : null}
        {triggerLabel}
      </button>
      {open ? (
        <Modal
          description={
            isEditing
              ? "Rename the set or adjust its pixel coordinates."
              : "Name the set and optionally type coordinates, or capture them with Draw ROIs."
          }
          onClose={() => setOpen(false)}
          title={isEditing ? "Edit ROI set" : "New ROI set"}
        >
          <RoiSetForm
            onClose={() => setOpen(false)}
            providerId={providerId}
            roiSet={roiSet}
          />
        </Modal>
      ) : null}
    </>
  );
}
