"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";

type SearchResult =
  | { kind: "commander"; id: string; name: string; color_identity: string[] | null }
  | { kind: "player"; topdeck_id: string; name: string };

const COLOR_CLASSES: Record<string, string> = {
  W: "bg-amber-200/80 text-amber-950",
  U: "bg-sky-500/90 text-white",
  B: "bg-purple-900/90 text-purple-100",
  R: "bg-red-500/90 text-white",
  G: "bg-emerald-500/90 text-white",
};

function ColorPip({ color }: { color: string }) {
  return (
    <span
      className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-semibold ${
        COLOR_CLASSES[color] ?? "bg-slate-500 text-white"
      }`}
    >
      {color}
    </span>
  );
}

export function HomeSearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      const pattern = `%${query.trim()}%`;

      const [commanderRes, playerRes] = await Promise.all([
        supabase
          .from("commander_stats")
          .select("commander_id, commander_name, color_identity")
          .ilike("commander_name", pattern)
          .not("commander_name", "ilike", "unknown commander")
          .order("total_entries", { ascending: false })
          .limit(5),
        supabase
          .from("players")
          .select("topdeck_id, name")
          .ilike("name", pattern)
          .not("topdeck_id", "is", null)
          .limit(5),
      ]);

      const commanders: SearchResult[] = (commanderRes.data ?? []).map((r) => ({
        kind: "commander",
        id: r.commander_id as string,
        name: r.commander_name as string,
        color_identity: (r.color_identity as string[] | null) ?? null,
      }));

      const players: SearchResult[] = (playerRes.data ?? []).map((r) => ({
        kind: "player",
        topdeck_id: r.topdeck_id as string,
        name: r.name as string,
      }));

      setResults([...commanders, ...players]);
      setOpen(true);
      setActiveIndex(-1);
      setLoading(false);
    }, 200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function navigate(result: SearchResult) {
    setOpen(false);
    setQuery("");
    if (result.kind === "commander") {
      router.push(`/commanders/${result.id}`);
    } else {
      router.push(`/regional-elo/player/${result.topdeck_id}`);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      navigate(results[activeIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-xl">
      <div className="flex items-center gap-2 rounded-xl border border-border/70 bg-muted/40 px-4 py-3 shadow-sm focus-within:border-primary/60 focus-within:ring-1 focus-within:ring-primary/30 transition">
        <svg
          className="h-4 w-4 shrink-0 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          placeholder="Search commanders or players…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          autoComplete="off"
          spellCheck={false}
        />
        {loading && (
          <svg
            className="h-4 w-4 shrink-0 animate-spin text-muted-foreground"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        )}
        {query && !loading && (
          <button
            type="button"
            className="shrink-0 text-muted-foreground hover:text-foreground transition"
            onClick={() => { setQuery(""); setOpen(false); inputRef.current?.focus(); }}
            aria-label="Clear"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {open && results.length > 0 && (
        <ul className="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-xl border border-border/60 bg-background shadow-xl">
          {results.map((result, i) => (
            <li key={result.kind === "commander" ? result.id : result.topdeck_id}>
              <button
                type="button"
                className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition ${
                  i === activeIndex ? "bg-muted" : "hover:bg-muted/60"
                }`}
                onMouseEnter={() => setActiveIndex(i)}
                onClick={() => navigate(result)}
              >
                {result.kind === "commander" ? (
                  <>
                    <span className="flex shrink-0 gap-0.5">
                      {(result.color_identity ?? []).filter(Boolean).map((c) => (
                        <ColorPip key={c} color={c} />
                      ))}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">
                      {normalizeDisplayString(result.name)}
                    </span>
                    <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                      commander
                    </span>
                  </>
                ) : (
                  <>
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted">
                      <svg className="h-3 w-3 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <circle cx="12" cy="8" r="4" />
                        <path d="M4 20c0-4 3.582-7 8-7s8 3 8 7" />
                      </svg>
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">
                      {result.name}
                    </span>
                    <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                      player
                    </span>
                  </>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      {open && query.trim().length >= 2 && !loading && results.length === 0 && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 rounded-xl border border-border/60 bg-background px-4 py-3 shadow-xl">
          <p className="text-sm text-muted-foreground">No commanders or players found.</p>
        </div>
      )}
    </div>
  );
}
