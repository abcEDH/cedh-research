import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

// Issue #321: CommanderArt prefers server-resolved Scryfall art (from
// scryfall_cards, joined in fetchers.ts) and only falls back to the live
// client-side hook for names missing from that map (cache misses).

vi.mock("@/hooks/use-scryfall-art", () => ({
  useScryfallArts: vi.fn(),
}));

vi.mock("@/components/commanders/art-crop-stack", () => ({
  ArtCropStack: ({ urls }: { urls: Array<string | null | undefined> }) =>
    React.createElement("div", { "data-testid": "art-crop-stack", "data-urls": JSON.stringify(urls) }),
}));

import { useScryfallArts } from "@/hooks/use-scryfall-art";
import { CommanderArt } from "@/components/commanders/commander-art";

function renderedUrls(html: string): Array<string | null> {
  const match = html.match(/data-urls="([^"]*)"/);
  if (!match) throw new Error("data-urls attribute not found in rendered output");
  return JSON.parse(match[1].replace(/&quot;/g, '"'));
}

describe("CommanderArt", () => {
  it("uses server-resolved art directly and requests no live lookups for a fully cached solo commander", () => {
    const mockUseScryfallArts = vi.mocked(useScryfallArts);
    mockUseScryfallArts.mockReturnValue({ ref: { current: null }, arts: [] });

    const html = renderToStaticMarkup(
      React.createElement(CommanderArt, {
        name: "Sisay, Weatherlight Captain",
        size: 40,
        artByName: { "Sisay, Weatherlight Captain": { artCrop: "https://x/sisay", normal: null } },
      })
    );

    expect(mockUseScryfallArts).toHaveBeenCalledWith([]);
    expect(renderedUrls(html)).toEqual(["https://x/sisay"]);
  });

  it("falls back to the live client hook when the name is a cache miss (not yet in artByName)", () => {
    const mockUseScryfallArts = vi.mocked(useScryfallArts);
    mockUseScryfallArts.mockReturnValue({
      ref: { current: null },
      arts: [{ artCrop: "https://x/live", normal: null, typeLine: null, setName: null }],
    });

    const html = renderToStaticMarkup(
      React.createElement(CommanderArt, { name: "Uncached Commander", size: 40, artByName: {} })
    );

    expect(mockUseScryfallArts).toHaveBeenCalledWith(["Uncached Commander"]);
    expect(renderedUrls(html)).toEqual(["https://x/live"]);
  });

  it("mixes server-resolved and client-fallback art for a partner pair with one cache miss", () => {
    const mockUseScryfallArts = vi.mocked(useScryfallArts);
    mockUseScryfallArts.mockReturnValue({
      ref: { current: null },
      arts: [{ artCrop: "https://x/kraum-live", normal: null, typeLine: null, setName: null }],
    });

    const html = renderToStaticMarkup(
      React.createElement(CommanderArt, {
        name: "Tymna the Weaver / Kraum, Ludevic's Opus",
        size: 40,
        artByName: { "Tymna the Weaver": { artCrop: "https://x/tymna-cached", normal: null } },
      })
    );

    // Only the cache-miss half (Kraum) is requested from the live hook.
    expect(mockUseScryfallArts).toHaveBeenCalledWith(["Kraum, Ludevic's Opus"]);
    expect(renderedUrls(html)).toEqual(["https://x/tymna-cached", "https://x/kraum-live"]);
  });

  it("passes null (not undefined) for a name that is neither cached nor fetched yet", () => {
    const mockUseScryfallArts = vi.mocked(useScryfallArts);
    mockUseScryfallArts.mockReturnValue({ ref: { current: null }, arts: [null] });

    const html = renderToStaticMarkup(
      React.createElement(CommanderArt, { name: "Brand New Commander", size: 40, artByName: {} })
    );

    expect(renderedUrls(html)).toEqual([null]);
  });

  it("requests no live lookups when both partner-pair names are already server-resolved", () => {
    const mockUseScryfallArts = vi.mocked(useScryfallArts);
    mockUseScryfallArts.mockReturnValue({ ref: { current: null }, arts: [] });

    const html = renderToStaticMarkup(
      React.createElement(CommanderArt, {
        name: "Tymna the Weaver / Kraum, Ludevic's Opus",
        size: 40,
        artByName: {
          "Tymna the Weaver": { artCrop: "https://x/tymna", normal: null },
          "Kraum, Ludevic's Opus": { artCrop: "https://x/kraum", normal: null },
        },
      })
    );

    expect(mockUseScryfallArts).toHaveBeenCalledWith([]);
    expect(renderedUrls(html)).toEqual(["https://x/tymna", "https://x/kraum"]);
  });
});
