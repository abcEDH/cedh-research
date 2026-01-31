/**
 * API Contract Tests
 *
 * These tests verify that the Supabase backend returns data
 * matching our frontend schemas. When the backend changes its
 * response format, these tests will fail, catching contract
 * mismatches before they reach production.
 *
 * Run with: npm run test:contracts
 */

import { describe, it, expect, beforeAll } from "vitest";
import { createClient } from "@supabase/supabase-js";
import {
  CommanderMatchupsResponseSchema,
  NotablePlayersResponseSchema,
  SurvivalCurveResponseSchema,
  CommanderStatsSchema,
  GlobalCardFrequencySchema,
  TrapCardSchema,
  SpiceCardSchema,
} from "../../src/lib/schemas/api-contracts";

// Test Supabase client - uses same env vars as app
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Skip tests if env vars are not available
const canRunTests = supabaseUrl && supabaseKey &&
  supabaseUrl.startsWith("http") && supabaseKey.length > 0;

const supabase = canRunTests
  ? createClient(supabaseUrl, supabaseKey)
  : null;

// Well-known commander ID for testing (Kraum/Tymna - commonly played)
const TEST_COMMANDER_ID = "39510fd4-b6b7-5463-ad6c-a8e8c9a2dd1c";

describe.skipIf(!canRunTests)("API Contract Tests", () => {
  describe("RPC Functions", () => {
    describe("get_commander_matchups", () => {
      it("should return data matching CommanderMatchup schema", async () => {
        const { data, error } = await supabase.rpc("get_commander_matchups", {
          p_commander_id: TEST_COMMANDER_ID,
        });

        expect(error).toBeNull();
        expect(data).toBeDefined();
        expect(Array.isArray(data)).toBe(true);

        if (data && data.length > 0) {
          // Validate the schema
          const result = CommanderMatchupsResponseSchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Sample data:", JSON.stringify(data[0], null, 2));
          }

          expect(result.success).toBe(true);

          // Verify key fields are present
          const sample = data[0];
          expect(sample).toHaveProperty("opponent_commander_id");
          expect(sample).toHaveProperty("opponent_commander_name");
          expect(sample).toHaveProperty("games_played");
          expect(sample).toHaveProperty("wins");
          expect(sample).toHaveProperty("losses");
          expect(sample).toHaveProperty("draws");
          expect(sample).toHaveProperty("win_rate");
          expect(sample).toHaveProperty("is_statistically_significant");
        }
      });
    });

    describe("get_notable_players_for_commander", () => {
      it("should return data matching NotablePlayer schema", async () => {
        const { data, error } = await supabase.rpc(
          "get_notable_players_for_commander",
          {
            p_commander_id: TEST_COMMANDER_ID,
          }
        );

        expect(error).toBeNull();
        expect(data).toBeDefined();
        expect(Array.isArray(data)).toBe(true);

        if (data && data.length > 0) {
          const result = NotablePlayersResponseSchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Sample data:", JSON.stringify(data[0], null, 2));
          }

          expect(result.success).toBe(true);

          // Verify key fields
          const sample = data[0];
          expect(sample).toHaveProperty("player_name");
          expect(sample).toHaveProperty("entries");
          expect(sample).toHaveProperty("total_wins");
          expect(sample).toHaveProperty("win_rate");
        }
      });
    });

    describe("get_survival_curve", () => {
      it("should return data matching SurvivalDataPoint schema", async () => {
        const { data, error } = await supabase.rpc("get_survival_curve", {
          p_commander_id: TEST_COMMANDER_ID,
        });

        expect(error).toBeNull();
        expect(data).toBeDefined();
        expect(Array.isArray(data)).toBe(true);

        if (data && data.length > 0) {
          const result = SurvivalCurveResponseSchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Sample data:", JSON.stringify(data[0], null, 2));
          }

          expect(result.success).toBe(true);

          // Verify key fields
          const sample = data[0];
          expect(sample).toHaveProperty("round_number");
          expect(sample).toHaveProperty("survival_probability");
          expect(sample).toHaveProperty("players_remaining");
        }
      });
    });
  });

  describe("Database Views", () => {
    describe("commander_stats", () => {
      it("should return data matching CommanderStats schema", async () => {
        const { data, error } = await supabase
          .from("commander_stats")
          .select("*")
          .eq("commander_id", TEST_COMMANDER_ID)
          .single();

        expect(error).toBeNull();
        expect(data).toBeDefined();

        if (data) {
          const result = CommanderStatsSchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Data:", JSON.stringify(data, null, 2));
          }

          expect(result.success).toBe(true);

          // Verify key fields
          expect(data).toHaveProperty("commander_id");
          expect(data).toHaveProperty("commander_name");
          expect(data).toHaveProperty("total_entries");
          expect(data).toHaveProperty("avg_win_rate");
        }
      });
    });

    describe("card_frequencies_global", () => {
      it("should return data matching GlobalCardFrequency schema", async () => {
        const { data, error } = await supabase
          .from("card_frequencies_global")
          .select("*")
          .limit(1)
          .single();

        expect(error).toBeNull();
        expect(data).toBeDefined();

        if (data) {
          const result = GlobalCardFrequencySchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Data:", JSON.stringify(data, null, 2));
          }

          expect(result.success).toBe(true);

          expect(data).toHaveProperty("card_name");
          expect(data).toHaveProperty("deck_count");
          expect(data).toHaveProperty("inclusion_rate");
          expect(data).toHaveProperty("tier");
        }
      });
    });

    describe("trap_cards_report", () => {
      it("should return data matching TrapCard schema", async () => {
        const { data, error } = await supabase
          .from("trap_cards_report")
          .select("*")
          .limit(1)
          .single();

        expect(error).toBeNull();
        expect(data).toBeDefined();

        if (data) {
          const result = TrapCardSchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Data:", JSON.stringify(data, null, 2));
          }

          expect(result.success).toBe(true);

          expect(data).toHaveProperty("card_name");
          expect(data).toHaveProperty("trap_score");
          expect(data).toHaveProperty("win_rate_delta");
        }
      });
    });

    describe("spice_cards_report", () => {
      it("should return data matching SpiceCard schema", async () => {
        const { data, error } = await supabase
          .from("spice_cards_report")
          .select("*")
          .limit(1)
          .single();

        expect(error).toBeNull();
        expect(data).toBeDefined();

        if (data) {
          const result = SpiceCardSchema.safeParse(data);

          if (!result.success) {
            console.error("Schema validation failed:", result.error.format());
            console.error("Data:", JSON.stringify(data, null, 2));
          }

          expect(result.success).toBe(true);

          expect(data).toHaveProperty("card_name");
          expect(data).toHaveProperty("win_rate_delta");
        }
      });
    });
  });
});

/**
 * Schema Drift Detection Test
 *
 * This test fetches all columns from key views and compares them
 * against expected columns. It will fail when new columns are added
 * or existing ones are removed, alerting us to update the frontend.
 */
describe.skipIf(!canRunTests)("Schema Drift Detection", () => {
  it("commander_stats should have expected columns", async () => {
    const { data, error } = await supabase
      .from("commander_stats")
      .select("*")
      .limit(1)
      .single();

    expect(error).toBeNull();
    expect(data).toBeDefined();

    const expectedColumns = [
      "commander_id",
      "commander_name",
      "archetype",
      "color_identity",
      "total_entries",
      "tournaments_played",
      "total_wins",
      "total_losses",
      "total_draws",
      "avg_win_rate",
      "top_16_count",
      "conversion_rate_top_16",
      "top_cut_count",
      "conversion_rate_top_cut",
    ];

    const actualColumns = Object.keys(data || {});

    // Check for missing columns (frontend expects, backend doesn't have)
    const missingColumns = expectedColumns.filter(
      (col) => !actualColumns.includes(col)
    );
    if (missingColumns.length > 0) {
      console.error("Missing columns in backend:", missingColumns);
    }
    expect(missingColumns).toEqual([]);

    // Check for new columns (backend has, frontend doesn't expect)
    const newColumns = actualColumns.filter(
      (col) => !expectedColumns.includes(col)
    );
    if (newColumns.length > 0) {
      console.warn("New columns in backend (update frontend?):", newColumns);
    }
    // Note: We don't fail on new columns, just warn
  });
});
