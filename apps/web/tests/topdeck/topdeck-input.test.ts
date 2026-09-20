import { describe, expect, it } from "vitest";
import { extractTopDeckTournamentUrl } from "@/lib/topdeck-input";
import { extractTournamentSlug } from "@/lib/topdeck";

const slug = "l7-summer-invitational-2026";
const url = `https://topdeck.gg/bracket/${slug}`;

describe("TopDeck mobile share text", () => {
  it.each([
    `L7 Summer Invitational 2026\n${url}\nJoin me!`,
    `Check out L7 Summer Invitational: ${url}`,
    `Join me at ${url} this weekend!`,
    `🏆 L7 Summer Invitational\r\n\r\n${url}?utm_source=share#standings`,
    `Check it out (${url}).`,
    `[L7 Summer Invitational](${url})`,
    `“${url}”`,
    `topdeck.gg/bracket/${slug}`,
    `HTTPS://WWW.TOPDECK.GG/bracket/${slug}/`,
    `https://example.com/other\n${url}`,
    `https://topdeck.gg/profile/some-player\n${url}`,
  ])("extracts the tournament from %s", (input) => {
    expect(extractTopDeckTournamentUrl(input)).toBe(url);
    expect(extractTournamentSlug(input)).toBe(slug);
  });

  it.each(["event", "bracket", "tournament", "tournaments"])("supports /%s links", (prefix) => {
    expect(extractTopDeckTournamentUrl(`Event: https://topdeck.gg/${prefix}/AbC_123-xyz`))
      .toBe(`https://topdeck.gg/${prefix}/AbC_123-xyz`);
  });

  it.each(["", slug, "Just a tournament title", "https://example.com/bracket/test", "https://fake-topdeck.gg/bracket/test", "https://topdeck.gg.example.com/bracket/test", "https://topdeck.gg/profile/player", "https://topdeck.gg/bracket/"])("does not rewrite unrelated text: %s", (input) => {
    expect(extractTopDeckTournamentUrl(input)).toBeNull();
  });

  it("keeps bare slug support", () => {
    expect(extractTournamentSlug(`  ${slug}  `)).toBe(slug);
  });

  it("uses the first tournament link when a message contains multiple", () => {
    expect(extractTopDeckTournamentUrl(`${url}\nhttps://topdeck.gg/event/other`)).toBe(url);
  });
});
