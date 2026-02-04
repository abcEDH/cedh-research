export function buildTopdeckProfileHref(idOrUsername: string | null | undefined): string | null {
  if (!idOrUsername) return null;
  const value = idOrUsername.trim();
  if (!value) return null;
  return `https://topdeck.gg/profile/${value}`;
}
