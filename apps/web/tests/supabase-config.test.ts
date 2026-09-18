import { describe, expect, it } from "vitest";
import {
  FALLBACK_SUPABASE_URL,
  resolveSupabaseUrl,
} from "@/lib/supabase-config";

describe("resolveSupabaseUrl", () => {
  it.each([undefined, "", "   ", "not-a-url", "ftp://supabase.example.com", "https://"]) (
    "uses the fallback for invalid URL %s",
    (value) => {
      expect(resolveSupabaseUrl(value)).toBe(FALLBACK_SUPABASE_URL);
    }
  );

  it("trims and preserves valid HTTP URLs", () => {
    expect(resolveSupabaseUrl("  https://supabase.example.com  ")).toBe(
      "https://supabase.example.com"
    );
    expect(resolveSupabaseUrl("http://localhost:54321")).toBe(
      "http://localhost:54321"
    );
  });
});
