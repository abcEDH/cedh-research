import type { EloTier } from "@/lib/elo-tiers";

export type PlayerPickerOption = {
  id: string;
  name: string;
  topdeck_id: string;
};

export function parseContentDispositionFilename(
  contentDisposition: string | null,
  fallback: string
) {
  if (!contentDisposition) return fallback;

  const encodedMatch = contentDisposition.match(
    /(?:^|;)\s*filename\*\s*=\s*UTF-8''([^;]*)/i
  );
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      // Fall through to the ASCII filename when the header is malformed.
    }
  }

  const plainMatch = contentDisposition.match(
    /(?:^|;)\s*filename\s*=\s*(?:"([^"]*)"|([^;]*))/i
  );
  return plainMatch?.[1] ?? plainMatch?.[2]?.trim() ?? fallback;
}

export async function searchPlayers(query: string, signal?: AbortSignal) {
  const response = await fetch(`/api/players/search?q=${encodeURIComponent(query)}`, { signal });
  if (!response.ok) throw new Error("Player search failed");
  const data = (await response.json()) as { players?: PlayerPickerOption[] };
  return data.players ?? [];
}

export async function fetchPlayerMatchupExport({
  player,
  dataType,
  tier,
}: {
  player: PlayerPickerOption;
  dataType: "detailed" | "summary";
  tier: EloTier;
}) {
  const params = new URLSearchParams({
    player_name: player.name,
    topdeck_id: player.topdeck_id,
    summary_only: dataType === "summary" ? "true" : "false",
    tier,
  });
  const response = await fetch(`/api/export/player-matchups?${params}`);

  if (!response.ok) {
    const errorData = (await response.json()) as { error?: string };
    throw new Error(errorData.error || "Export failed");
  }

  const fallback = `${player.name.replace(/\s+/g, "_")}_matchups${
    dataType === "summary" ? "_summary" : ""
  }.json`;
  return {
    blob: await response.blob(),
    fileName: parseContentDispositionFilename(response.headers.get("content-disposition"), fallback),
  };
}
