/** Returns true if the commander name is a real name (non-null, non-empty, not "unknown commander"). */
export function isKnownCommanderName(value: string | null | undefined): value is string {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}
