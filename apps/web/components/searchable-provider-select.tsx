"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { SearchIcon } from "@/components/icons";
import { searchProvidersAction } from "@/lib/actions";
import type { GameProvider } from "@/lib/api";

export interface SearchableProviderSelectProps {
  label: string;
  value: number | null;
  initialProviders: GameProvider[];
  onChange: (provider: GameProvider | null) => void;
  selectedProvider?: GameProvider | null;
  hint?: string;
  disabled?: boolean;
}

/**
 * Combobox for choosing a game provider.
 *
 * Filters the server-supplied provider list immediately, then queries the
 * provider endpoint for searches so newly created providers outside the
 * initial page are still reachable.
 */
export function SearchableProviderSelect({
  label,
  value,
  initialProviders,
  onChange,
  selectedProvider,
  hint,
  disabled = false,
}: SearchableProviderSelectProps) {
  const inputId = useId();
  const listId = `${inputId}-listbox`;
  const containerRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<GameProvider[]>(initialProviders);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);

  const selected =
    selectedProvider ??
    initialProviders.find((provider) => provider.id === value) ??
    (value !== null
      ? { id: value, name: `Provider #${value}` }
      : null);

  const trimmedQuery = query.trim();
  const displayValue = open ? query : (selected?.name ?? "");
  const emptyMessage = trimmedQuery
    ? "No providers match that search."
    : initialProviders.length === 0
      ? "No providers yet. Create a provider first."
      : "No providers found.";

  useEffect(() => {
    if (!open) {
      return;
    }

    // Invalidate any in-flight search as soon as the query changes so an
    // older response cannot overwrite the current list.
    const currentRequest = requestId.current + 1;
    requestId.current = currentRequest;

    if (!trimmedQuery) {
      setOptions(initialProviders);
      setLoading(false);
      return;
    }

    setLoading(true);

    const timer = window.setTimeout(async () => {
      const results = await searchProvidersAction(trimmedQuery);
      if (requestId.current !== currentRequest) {
        return;
      }
      setOptions(results);
      setLoading(false);
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [open, trimmedQuery, initialProviders]);

  useEffect(() => {
    setActiveIndex(-1);
  }, [options]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
        setQuery("");
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [open]);

  const choose = (provider: GameProvider) => {
    onChange(provider);
    setOpen(false);
    setQuery("");
    setActiveIndex(-1);
  };

  const closeList = () => {
    setOpen(false);
    setQuery("");
    setActiveIndex(-1);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        setActiveIndex(options.length > 0 ? 0 : -1);
        return;
      }
      setActiveIndex((current) =>
        options.length === 0 ? -1 : (current + 1) % options.length,
      );
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        setActiveIndex(options.length > 0 ? options.length - 1 : -1);
        return;
      }
      setActiveIndex((current) =>
        options.length === 0
          ? -1
          : current <= 0
            ? options.length - 1
            : current - 1,
      );
      return;
    }

    if (event.key === "Enter" && open) {
      const active = activeIndex >= 0 ? options[activeIndex] : undefined;
      if (active) {
        event.preventDefault();
        choose(active);
      }
      return;
    }

    if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      closeList();
      return;
    }

    if (event.key === "Tab") {
      closeList();
    }
  };

  return (
    <div className="form-field" ref={containerRef}>
      <label className="form-label" htmlFor={inputId}>
        {label}
      </label>
      <div className="combobox">
        <div className="combobox-input-wrap">
          <SearchIcon />
          <input
            aria-autocomplete="list"
            aria-controls={listId}
            aria-expanded={open}
            aria-activedescendant={
              open && activeIndex >= 0 && options[activeIndex]
                ? `${listId}-option-${options[activeIndex].id}`
                : undefined
            }
            aria-required="true"
            autoComplete="off"
            className="input"
            disabled={disabled}
            id={inputId}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpen(true);
              // Typing starts a new selection; require the user to pick a
              // provider from the filtered list before submitting.
              if (value !== null) {
                onChange(null);
              }
            }}
            onClick={() => setOpen(true)}
            onFocus={(event) => {
              setOpen(true);
              event.currentTarget.select();
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              open
                ? "Type to search providers…"
                : (selected?.name ?? "Search providers…")
            }
            role="combobox"
            type="text"
            value={displayValue}
          />
        </div>

        {open ? (
          <ul className="combobox-list" id={listId} role="listbox">
            {loading ? (
              <li className="combobox-status" role="presentation">
                Searching…
              </li>
            ) : null}
            {!loading && options.length === 0 ? (
              <li className="combobox-status" role="presentation">
                {emptyMessage}
              </li>
            ) : null}
            {!loading
              ? options.map((provider, index) => (
                  <li
                    aria-selected={provider.id === value}
                    className="combobox-option"
                    data-active={index === activeIndex}
                    id={`${listId}-option-${provider.id}`}
                    key={provider.id}
                    onClick={() => choose(provider)}
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setActiveIndex(index)}
                    role="option"
                  >
                    <span>{provider.name}</span>
                    <span className="combobox-option-id">
                      #{provider.id}
                    </span>
                  </li>
                ))
              : null}
          </ul>
        ) : null}
      </div>
      {hint ? <p className="form-hint">{hint}</p> : null}
    </div>
  );
}
