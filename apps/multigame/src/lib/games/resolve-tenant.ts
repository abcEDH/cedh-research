import { DEFAULT_GAME, isGameSlug, type GameSlug } from "@/lib/games/registry";

/**
 * Pure tenant resolution shared by the proxy (Next middleware) and tests.
 *
 * Resolution order:
 *   1. `null` when the path already targets an internal /[game]/ tree
 *      (the proxy passes those through untouched)
 *   2. `?game=<slug>` query override (local dev / Vercel previews)
 *   3. first hostname label (riftbound.tedh.gg / riftbound.localhost)
 *   4. NEXT_PUBLIC_DEFAULT_GAME env, falling back to "riftbound"
 */
export function resolveTenantSlug({
  pathname,
  queryGame,
  host,
}: {
  pathname: string;
  queryGame: string | null;
  host: string | null;
}): GameSlug | null {
  const firstSegment = pathname.split("/")[1];
  if (isGameSlug(firstSegment)) {
    return null;
  }

  if (isGameSlug(queryGame)) {
    return queryGame;
  }

  const hostLabel = (host ?? "").split(":")[0].split(".")[0];
  if (isGameSlug(hostLabel)) {
    return hostLabel;
  }

  return DEFAULT_GAME;
}
