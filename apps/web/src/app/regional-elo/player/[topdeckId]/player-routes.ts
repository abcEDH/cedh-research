export function buildPlayerVersusHref(
  playerTopdeckId: string,
  opponentTopdeckId: string,
  eloOnly = false
) {
  const path = `/regional-elo/player/${playerTopdeckId}/vs/${opponentTopdeckId}`;
  return eloOnly ? `${path}?eloOnly=true` : path;
}
