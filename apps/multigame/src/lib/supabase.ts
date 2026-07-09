import { createClient } from "@supabase/supabase-js";

// Placeholder fallbacks keep `next build` working without live credentials
// (mirrors apps/web). Fetchers catch query failures and return empty results,
// so pages render an empty state instead of crashing.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export function isSupabaseConfigured(): boolean {
  return !supabaseUrl.includes("placeholder.supabase.co") && supabaseAnonKey !== "placeholder";
}
