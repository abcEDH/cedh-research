import { describe, expect, it } from "vitest";
import { canonicalRegionKey } from "@/lib/region-name-normalization";

describe("legacy region filters", () => {
  it("resolves full names and unambiguous abbreviations", () => {
    expect(canonicalRegionKey("TX")).toBe("TEXAS");
    expect(canonicalRegionKey("California")).toBe("CALIFORNIA");
    expect(canonicalRegionKey("CA", "US")).toBe("CALIFORNIA");
  });
  it("requires country context for ambiguous codes", () => {
    expect(canonicalRegionKey("WA")).toBe("WA");
    expect(canonicalRegionKey("WA", "Australia")).toBe("WESTERN AUSTRALIA");
    expect(canonicalRegionKey("WA", "United States")).toBe("WASHINGTON");
  });
  it("preserves unknown and conflicting values", () => {
    expect(canonicalRegionKey("BC", "US")).toBe("BC");
    expect(canonicalRegionKey("Baja California")).toBe("BAJA CALIFORNIA");
  });
});
