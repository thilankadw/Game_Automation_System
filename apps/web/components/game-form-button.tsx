"use client";

import { useState } from "react";

import { GameForm } from "@/components/game-form";
import { PlusIcon } from "@/components/icons";
import { Modal } from "@/components/modal";
import type { Game, GameProvider } from "@/lib/api";

export interface GameFormButtonProps {
  providers: GameProvider[];
  game?: Game | null;
  triggerLabel: string;
  triggerClassName?: string;
}

/**
 * Trigger button that opens the create or edit game dialog.
 */
export function GameFormButton({
  providers,
  game,
  triggerLabel,
  triggerClassName = "button button-primary",
}: GameFormButtonProps) {
  const [open, setOpen] = useState(false);
  const isEditing = Boolean(game);

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
              ? "Update the catalog entry and its provider."
              : "Add a title, point it at a provider, and set its automation spins."
          }
          onClose={() => setOpen(false)}
          title={isEditing ? "Edit game" : "New game"}
        >
          <GameForm
            game={game}
            onClose={() => setOpen(false)}
            providers={providers}
          />
        </Modal>
      ) : null}
    </>
  );
}
