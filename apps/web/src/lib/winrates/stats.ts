/**
 * Pure math/formatting for the /winrates matrix page (#150). No data fetching here -- see
 * `fetchers.ts` for the Supabase RPC calls and `components/winrates/matchup-matrix-table.tsx`
 * for the presentational table that consumes these helpers.
 */
import type { WinrateMatrixRow, CommanderMetaEv } from "@/lib/schemas/api-contracts";
import type { CommanderLabel } from "./fetchers";

export type HeatBucket = "cold" | "cool" | "warm" | "hot";

/**
 * mtgdecks.net's 4-step heat scale on point_winrate: <30% dark red, 30-49% orange, 50-59%
 * mustard, >=60% olive-green. The CI itself is the "small sample" warning (a wide band on a
 * low-N cell self-flags visually) -- no separate asterisk/marker is layered on top.
 */
export function classifyWinrateHeat(pointWinrate: number): HeatBucket {
  if (pointWinrate < 0.3) return "cold";
  if (pointWinrate < 0.5) return "cool";
  if (pointWinrate < 0.6) return "warm";
  return "hot";
}

/**
 * Tailwind arbitrary-value classes reading the --knd-heat-* tokens (globals.css). Rendered as a
 * low-alpha tint over the existing surface rather than a solid fill, so the cell's own text
 * (point winrate, CI, sample size) stays in normal text-ink colors per house convention -- the
 * heat color is a secondary channel, never the only one, since every cell also prints its exact
 * numbers.
 */
export const HEAT_BG_CLASS: Record<HeatBucket, string> = {
  cold: "bg-[hsl(var(--knd-heat-cold)/0.30)]",
  cool: "bg-[hsl(var(--knd-heat-cool)/0.26)]",
  warm: "bg-[hsl(var(--knd-heat-warm)/0.24)]",
  hot: "bg-[hsl(var(--knd-heat-hot)/0.26)]",
};

export const HEAT_LEGEND: { bucket: HeatBucket; label: string }[] = [
  { bucket: "cold", label: "< 30%" },
  { bucket: "cool", label: "30–49%" },
  { bucket: "warm", label: "50–59%" },
  { bucket: "hot", label: "≥ 60%" },
];

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatCiRange(low: number | null | undefined, high: number | null | undefined): string {
  if (low === null || low === undefined || high === null || high === undefined) return "—";
  return `${formatPercent(low)}–${formatPercent(high)}`;
}

export function formatSampleSize(n: number): string {
  const count = n.toLocaleString();
  return `${count} match${n === 1 ? "" : "es"}`;
}

/** Row/column cell lookup key. deck_b null (the OVERALL row) is normalized to the sentinel. */
export function cellKey(a: string, b: string | null): string {
  return `${a}:${b ?? "OVERALL"}`;
}

export interface MatrixRowBundle {
  commander: CommanderLabel;
  overall: WinrateMatrixRow | null;
  ev: CommanderMetaEv | null;
  cellsByOpponent: Map<string, WinrateMatrixRow>;
}

/**
 * Groups the flat RPC rows by deck_a so the table can render one row per commander with O(1)
 * lookup per opponent column, instead of re-scanning the full row list per cell.
 */
export function buildRowBundles(
  commanderOrder: CommanderLabel[],
  matrixRows: WinrateMatrixRow[],
  evRows: CommanderMetaEv[]
): MatrixRowBundle[] {
  // Built from a plain array (not a Map) because this is called from a Client Component that
  // received its props across the server/client boundary, where only JSON-serializable values
  // survive -- a Map would not.
  const evByCommander = new Map(evRows.map((row) => [row.commander_id, row]));
  const byCommander = new Map<string, { overall: WinrateMatrixRow | null; cells: Map<string, WinrateMatrixRow> }>();
  for (const commander of commanderOrder) {
    byCommander.set(commander.id, { overall: null, cells: new Map() });
  }

  for (const row of matrixRows) {
    const bucket = byCommander.get(row.deck_a_commander_id);
    if (!bucket) continue; // defensive: RPC is expected to only return top-N deck_a rows
    if (row.deck_b_commander_id === null) {
      bucket.overall = row;
    } else {
      bucket.cells.set(row.deck_b_commander_id, row);
    }
  }

  return commanderOrder.map((commander) => {
    const bucket = byCommander.get(commander.id);
    return {
      commander,
      overall: bucket?.overall ?? null,
      ev: evByCommander.get(commander.id) ?? null,
      cellsByOpponent: bucket?.cells ?? new Map(),
    };
  });
}

export type MatrixSortKey = "matches" | "winrate" | "ev" | "alphabetical";
export type SortDirection = "asc" | "desc";

export const DEFAULT_SORT_KEY: MatrixSortKey = "matches";

function sortComparable(bundle: MatrixRowBundle, key: MatrixSortKey): number | string {
  switch (key) {
    case "matches":
      return bundle.overall?.games_played ?? 0;
    case "winrate":
      return bundle.overall?.point_winrate ?? -1;
    case "ev":
      return bundle.ev?.meta_ev ?? -1;
    case "alphabetical":
      return bundle.commander.name.toLowerCase();
    default:
      return 0;
  }
}

/**
 * Sorts rows only -- columns stay fixed per #150's acceptance criteria ("Sort controls above
 * the table: ... rows only, columns stay fixed"). Pure and synchronous: no re-fetch.
 */
export function sortRowBundles(
  bundles: MatrixRowBundle[],
  key: MatrixSortKey,
  direction: SortDirection
): MatrixRowBundle[] {
  const sorted = [...bundles].sort((a, b) => {
    const left = sortComparable(a, key);
    const right = sortComparable(b, key);
    if (typeof left === "string" || typeof right === "string") {
      return String(left).localeCompare(String(right));
    }
    return left - right;
  });
  return direction === "asc" ? sorted : sorted.reverse();
}

/** Header row repeats every N data rows for scroll-readability on a long matrix (#150). */
export const HEADER_REPEAT_INTERVAL = 30;

export const DAYS_BACK_OPTIONS = [
  { value: 180, label: "Last 180 days" },
  { value: 60, label: "Last 60 days" },
  { value: 30, label: "Last 30 days" },
  { value: 15, label: "Last 15 days" },
] as const;

export const DEFAULT_DAYS_BACK = 180;

export function parseDaysBack(raw: string | string[] | undefined): number {
  const value = Array.isArray(raw) ? raw[0] : raw;
  const parsed = value ? Number.parseInt(value, 10) : NaN;
  const allowed = DAYS_BACK_OPTIONS.map((o) => o.value);
  return allowed.includes(parsed as (typeof allowed)[number]) ? parsed : DEFAULT_DAYS_BACK;
}
