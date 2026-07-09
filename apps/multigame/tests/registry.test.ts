import { describe, expect, it } from "vitest";
import {
  DEFAULT_GAME,
  GAME_SLUGS,
  getGame,
  isGameSlug,
  resolveFormat,
} from "@/lib/games/registry";

describe("game registry", () => {
  it("exposes at least the three launch tenants", () => {
    expect(GAME_SLUGS).toEqual(expect.arrayContaining(["riftbound", "gundam", "retro"]));
  });

  it("resolves every slug to a config whose slug matches", () => {
    for (const slug of GAME_SLUGS) {
      const game = getGame(slug);
      expect(game).not.toBeNull();
      expect(game?.slug).toBe(slug);
    }
  });

  it("has unique hostnames and matching baseUrls", () => {
    const hostnames = GAME_SLUGS.map((slug) => getGame(slug)!.hostname);
    expect(new Set(hostnames).size).toBe(hostnames.length);
    for (const slug of GAME_SLUGS) {
      const game = getGame(slug)!;
      expect(game.baseUrl).toBe(`https://${game.hostname}`);
    }
  });

  it("keeps defaultFormat within formats", () => {
    for (const slug of GAME_SLUGS) {
      const game = getGame(slug)!;
      expect(game.formats.length).toBeGreaterThan(0);
      expect(game.formats.map((format) => format.slug)).toContain(game.defaultFormat);
    }
  });

  it("has non-empty compliance and db discriminator strings", () => {
    for (const slug of GAME_SLUGS) {
      const game = getGame(slug)!;
      expect(game.compliance.fanContentNotice.length).toBeGreaterThan(0);
      expect(game.compliance.copyrightHolder.length).toBeGreaterThan(0);
      expect(game.dbGame.length).toBeGreaterThan(0);
      expect(game.identityNoun.length).toBeGreaterThan(0);
    }
  });

  it("rejects junk slugs, including prototype keys", () => {
    expect(isGameSlug("riftbound")).toBe(true);
    expect(isGameSlug("")).toBe(false);
    expect(isGameSlug("magic")).toBe(false);
    expect(isGameSlug("RIFTBOUND")).toBe(false);
    expect(isGameSlug(null)).toBe(false);
    expect(isGameSlug(undefined)).toBe(false);
    expect(isGameSlug(42)).toBe(false);
    expect(isGameSlug("toString")).toBe(false);
    expect(isGameSlug("__proto__")).toBe(false);
    expect(getGame("toString")).toBeNull();
  });

  it("has a valid DEFAULT_GAME", () => {
    expect(isGameSlug(DEFAULT_GAME)).toBe(true);
  });

  describe("resolveFormat", () => {
    it("matches a known slug", () => {
      const retro = getGame("retro")!;
      expect(resolveFormat(retro, "goat").slug).toBe("goat");
    });

    it("falls back to defaultFormat for unknown or missing slugs", () => {
      const retro = getGame("retro")!;
      expect(resolveFormat(retro, "nonsense").slug).toBe(retro.defaultFormat);
      expect(resolveFormat(retro, undefined).slug).toBe(retro.defaultFormat);
    });
  });
});
