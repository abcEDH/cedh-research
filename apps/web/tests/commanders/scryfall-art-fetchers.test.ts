import { describe, expect, it, vi, beforeEach } from "vitest";

// Issue #321: fetchers.ts joins against the `scryfall_cards` table (populated
// by packages/backend/src/ingest_scryfall_cards.py from Scryfall's bulk-data
// dump) to server-render art_crop/normal URLs instead of depending on a live
// client-side fetch per card name.

let mockSelectResult: { data: unknown; error: unknown } = { data: [], error: null };
let lastFromTable: string | null = null;
let lastInColumn: string | null = null;
let lastInValues: unknown[] | null = null;

vi.mock("@/lib/supabase", () => ({
  supabase: {
    from: (table: string) => {
      lastFromTable = table;
      const chain = {
        select: () => chain,
        in: (column: string, values: unknown[]) => {
          lastInColumn = column;
          lastInValues = values;
          return Promise.resolve(mockSelectResult);
        },
      };
      return chain;
    },
  },
}));

import { getCommanderArtByName, getScryfallArtByNames } from "@/lib/commanders/fetchers";

describe("getScryfallArtByNames", () => {
  beforeEach(() => {
    mockSelectResult = { data: [], error: null };
    lastFromTable = null;
    lastInColumn = null;
    lastInValues = null;
  });

  it("returns an empty map without querying when given no names", async () => {
    const result = await getScryfallArtByNames([]);

    expect(result).toEqual({});
    expect(lastFromTable).toBeNull();
  });

  it("queries scryfall_cards with deduplicated names", async () => {
    mockSelectResult = { data: [], error: null };

    await getScryfallArtByNames(["Sol Ring", "Sol Ring", "Rhystic Study"]);

    expect(lastFromTable).toBe("scryfall_cards");
    expect(lastInColumn).toBe("name");
    expect(lastInValues).toEqual(["Sol Ring", "Rhystic Study"]);
  });

  it("maps image_uris.art_crop and .normal onto each returned name", async () => {
    mockSelectResult = {
      data: [
        { name: "Sol Ring", image_uris: { art_crop: "https://x/sol-crop", normal: "https://x/sol-normal" } },
      ],
      error: null,
    };

    const result = await getScryfallArtByNames(["Sol Ring"]);

    expect(result).toEqual({
      "Sol Ring": { artCrop: "https://x/sol-crop", normal: "https://x/sol-normal" },
    });
  });

  it("omits names not present in scryfall_cards (cache misses)", async () => {
    mockSelectResult = { data: [], error: null };

    const result = await getScryfallArtByNames(["Not Cached Yet"]);

    expect(result).toEqual({});
  });

  it("returns an empty map and logs on a query error rather than throwing", async () => {
    mockSelectResult = { data: null, error: { message: "boom" } };
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const result = await getScryfallArtByNames(["Sol Ring"]);

    expect(result).toEqual({});
    expect(consoleErrorSpy).toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("handles a row with a null image_uris by returning null art fields", async () => {
    mockSelectResult = {
      data: [{ name: "No Art Yet", image_uris: null }],
      error: null,
    };

    const result = await getScryfallArtByNames(["No Art Yet"]);

    expect(result).toEqual({ "No Art Yet": { artCrop: null, normal: null } });
  });
});

describe("getCommanderArtByName", () => {
  beforeEach(() => {
    mockSelectResult = { data: [], error: null };
    lastInValues = null;
  });

  it("splits a partner pair display name and queries both individual faces", async () => {
    mockSelectResult = {
      data: [
        { name: "Tymna the Weaver", image_uris: { art_crop: "https://x/tymna", normal: null } },
        { name: "Kraum, Ludevic's Opus", image_uris: { art_crop: "https://x/kraum", normal: null } },
      ],
      error: null,
    };

    const result = await getCommanderArtByName("Tymna the Weaver / Kraum, Ludevic's Opus");

    expect(lastInValues).toEqual(["Tymna the Weaver", "Kraum, Ludevic's Opus"]);
    expect(result).toEqual({
      "Tymna the Weaver": { artCrop: "https://x/tymna", normal: null },
      "Kraum, Ludevic's Opus": { artCrop: "https://x/kraum", normal: null },
    });
  });

  it("queries a single name for a solo commander", async () => {
    mockSelectResult = { data: [], error: null };

    await getCommanderArtByName("Sisay, Weatherlight Captain");

    expect(lastInValues).toEqual(["Sisay, Weatherlight Captain"]);
  });
});
