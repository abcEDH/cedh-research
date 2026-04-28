export function buildTopdeckProfileHref(idOrUsername: string | null | undefined): string | null {
  if (!idOrUsername) return null;
  const value = idOrUsername.trim();
  if (!value) return null;
  return `https://topdeck.gg/profile/${value}`;
}

export function buildTopdeckTournamentUrl(slug: string | null | undefined): string | null {
  return slug ? `https://topdeck.gg/bracket/${slug}` : null;
}

export function buildTopdeckDecklistUrl(
  tournamentSlug: string | null | undefined,
  topdeckId: string | null | undefined
): string | null {
  return tournamentSlug && topdeckId ? `https://topdeck.gg/deck/${tournamentSlug}/${topdeckId}` : null;
}
