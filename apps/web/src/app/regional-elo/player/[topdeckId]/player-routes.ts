export function buildPlayerVersusHref(playerTopdeckId: string, opponentTopdeckId: string) {
  return `/regional-elo/player/${playerTopdeckId}/vs/${opponentTopdeckId}`;
}
