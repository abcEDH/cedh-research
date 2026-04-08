import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchTournamentBySlug } from "@/lib/topdeck";

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
