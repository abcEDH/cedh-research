export const FALLBACK_SUPABASE_URL = "https://placeholder.supabase.co";

export function resolveSupabaseUrl(rawUrl: string | undefined): string {
  const candidate = rawUrl?.trim();

  if (!candidate) return FALLBACK_SUPABASE_URL;

  try {
    const parsed = new URL(candidate);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return candidate;
    }
  } catch {
    // Fall through to the build-safe placeholder for malformed environments.
  }

  return FALLBACK_SUPABASE_URL;
}
