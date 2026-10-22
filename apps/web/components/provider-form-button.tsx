"use client";

import { useState } from "react";

import { PlusIcon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { ProviderForm } from "@/components/provider-form";
import type { GameProvider } from "@/lib/api";

export interface ProviderFormButtonProps {
  provider?: GameProvider | null;
  triggerLabel: string;
  triggerClassName?: string;
}

/**
 * Trigger button that opens the create or edit provider dialog.
 */
export function ProviderFormButton({
  provider,
  triggerLabel,
  triggerClassName = "button button-primary",
}: ProviderFormButtonProps) {
  const [open, setOpen] = useState(false);
  const isEditing = Boolean(provider);

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
              ? "Rename the provider everywhere it appears."
              : "Create a provider to group games and ROI sets."
          }
          onClose={() => setOpen(false)}
          title={isEditing ? "Edit provider" : "New provider"}
        >
          <ProviderForm provider={provider} onClose={() => setOpen(false)} />
        </Modal>
      ) : null}
    </>
  );
}
