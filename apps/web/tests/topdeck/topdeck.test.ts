import { afterEach, describe, expect, it, vi } from "vitest";

import {
  defaultTournamentStructureForPlayerCount,
  fetchTournamentBySlug,
  inferTournamentStructureFromText,
} from "@/lib/topdeck";

function createJsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: vi.fn(async () => payload),
    text: vi.fn(async () => JSON.stringify(payload)),
  } as Response;
}

describe("fetchTournamentBySlug", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    delete process.env.TOPDECK_API_KEY;
  });

  it("waits for Retry-After HTTP-date values before retrying", async () => {
    vi.stubGlobal("fetch", vi.fn());
    vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-04-08T00:00:00Z"));
    vi.spyOn(globalThis, "setTimeout").mockImplementation(((callback: TimerHandler) => {
      if (typeof callback === "function") {
        callback();
      }
      return 0 as unknown as NodeJS.Timeout;
    }) as typeof setTimeout);

    process.env.TOPDECK_API_KEY = "test-key";
    const fetchMock = vi.mocked(globalThis.fetch);
    fetchMock
      .mockResolvedValueOnce(
        new Response("rate limited", {
          status: 429,
          headers: {
            "Retry-After": "Wed, 08 Apr 2026 00:01:00 GMT",
          },
        })
      )
      .mockResolvedValueOnce(
        createJsonResponse({
          data: {
            name: "Example",
            game: "Magic",
            format: "cEDH",
            startDate: "2026-04-08",
          },
          standings: [
            {
              name: "Player One",
              id: "player-1",
              standing: 1,
              points: 9,
              successRate: 0.75,
              opponentSuccessRate: 0.5,
              wins: 0,
              draws: 0,
              losses: 0,
              decklist: null,
              deckObj: null,
              actualDeckCommander: null,
              actualDecklistUrl: null,
            },
          ],
          rounds: [],
        })
      );

    const result = await fetchTournamentBySlug("example-slug");

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.standings[0].winRate).toBe(0.75);
    expect(result.standings[0].opponentWinRate).toBe(0.5);
    expect(globalThis.setTimeout).toHaveBeenCalledWith(expect.any(Function), 60000);
  });
});

describe("inferTournamentStructureFromText", () => {
  it("reads six swiss rounds and cut to Top 40 from event page text", () => {
    const result = inferTournamentStructureFromText(`
      <main>
        <p>Competitive cEDH event</p>
        <p>6 Rounds of Swiss</p>
        <p>Cut to Top 40</p>
      </main>
    `);

    expect(result).toEqual({
      swissRounds: 6,
      topCut: 40,
      source: "event_page",
    });
  });

  it("handles compact top-cut text and alternate swiss labels", () => {
    const result = inferTournamentStructureFromText("Swiss: 7 Rounds followed by Top16 Cut");

    expect(result?.swissRounds).toBe(7);
    expect(result?.topCut).toBe(16);
  });

  it("reads the Quest event-page structure wording", () => {
    const result = inferTournamentStructureFromText(`
      <b>6 Swiss</b> Rounds (incl. Break)
      After Day 1 (6 Rounds of Swiss), <b>Top 40 will be invited back for Day 2</b>
      <span>What's a Top 40 Cut?</span>
    `);

    expect(result?.swissRounds).toBe(6);
    expect(result?.topCut).toBe(40);
  });

  it("returns null when the event page has no usable structure", () => {
    expect(inferTournamentStructureFromText("<p>Registration is open.</p>")).toBeNull();
  });
});

describe("defaultTournamentStructureForPlayerCount", () => {
  it.each([
    [16, 2, 0],
    [17, 3, 4],
    [34, 3, 4],
    [35, 4, 10],
    [64, 4, 10],
    [65, 5, 16],
    [128, 5, 16],
    [129, 6, 16],
    [208, 6, 16],
    [209, 7, 16],
    [304, 7, 16],
    [305, 8, 16],
    [540, 8, 16],
    [541, 9, 16],
    [960, 9, 16],
    [961, 10, 16],
  ])("uses TopDeck addendum fallback for %i players", (players, swissRounds, topCut) => {
    expect(defaultTournamentStructureForPlayerCount(players)).toEqual({
      swissRounds,
      topCut,
      source: "fallback",
    });
  });
});
