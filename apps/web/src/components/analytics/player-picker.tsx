"use client";

import { useEffect, useState } from "react";

export type PlayerPickerOption = {
  id: string;
  name: string;
  topdeck_id: string;
};

export function PlayerPicker({
  disabled = false,
  selectedPlayer,
  onSelect,
}: {
  disabled?: boolean;
  selectedPlayer: PlayerPickerOption | null;
  onSelect: (player: PlayerPickerOption | null) => void;
}) {
  const [query, setQuery] = useState(selectedPlayer?.name ?? "");
  const [options, setOptions] = useState<PlayerPickerOption[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 2 || selectedPlayer?.name === query) {
      setOptions([]);
      setIsSearching(false);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setIsSearching(true);
      try {
        const response = await fetch(
          `/api/players/search?q=${encodeURIComponent(trimmedQuery)}`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error("Player search failed");
        const data = (await response.json()) as { players?: PlayerPickerOption[] };
        setOptions(data.players ?? []);
        setIsOpen(true);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setOptions([]);
        }
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query, selectedPlayer]);

  function handleChange(value: string) {
    setQuery(value);
    if (selectedPlayer) onSelect(null);
    setIsOpen(value.trim().length >= 2);
  }

  function selectPlayer(player: PlayerPickerOption) {
    setQuery(player.name);
    setOptions([]);
    setIsOpen(false);
    onSelect(player);
  }

  return (
    <div className="relative">
      <label htmlFor="player" className="mb-2 block text-sm font-medium">
        Player
      </label>
      <div className="relative">
        <input
          id="player"
          type="search"
          value={query}
          onChange={(event) => handleChange(event.target.value)}
          onFocus={() => setIsOpen(query.trim().length >= 2 && !selectedPlayer)}
          placeholder="Search by player name"
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls="player-search-results"
          className="min-h-11 w-full rounded-lg border border-slate-600 bg-slate-700 px-4 py-2 pr-12 text-white placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
          disabled={disabled}
        />
        {query ? (
          <button
            type="button"
            aria-label="Clear selected player"
            onClick={() => {
              setQuery("");
              setOptions([]);
              setIsOpen(false);
              onSelect(null);
            }}
            className="absolute right-2 top-1/2 min-h-11 min-w-11 -translate-y-1/2 rounded-md text-slate-300 hover:bg-slate-600 hover:text-white"
            disabled={disabled}
          >
            ×
          </button>
        ) : null}
      </div>
      {isSearching ? <p className="mt-2 text-xs text-slate-400">Searching players…</p> : null}
      {isOpen && !selectedPlayer && options.length > 0 ? (
        <ul
          id="player-search-results"
          role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-slate-600 bg-slate-800 p-1 shadow-xl"
        >
          {options.map((player) => (
            <li key={player.topdeck_id} role="option" aria-selected={false}>
              <button
                type="button"
                onClick={() => selectPlayer(player)}
                className="flex min-h-11 w-full items-center justify-between rounded-md px-3 py-2 text-left hover:bg-slate-700"
              >
                <span className="truncate text-white">{player.name}</span>
                <span className="ml-3 shrink-0 text-xs text-slate-400">Select</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {query.trim().length >= 2 && !selectedPlayer && !isSearching && isOpen && options.length === 0 ? (
        <p className="mt-2 text-xs text-slate-400">No matching players found.</p>
      ) : null}
      {selectedPlayer ? (
        <p className="mt-2 text-xs text-emerald-300">
          Selected: {selectedPlayer.name}
        </p>
      ) : (
        <p className="mt-2 text-xs text-slate-400">Choose a player from the search results.</p>
      )}
    </div>
  );
}
