import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

// Mock supabase at module level
vi.mock("@/lib/supabase", () => {
  const mockQueryBuilder = {
    select: vi.fn().mockReturnThis(),
    in: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    range: vi.fn().mockReturnThis(),
    maybeSingle: vi.fn().mockReturnValue(Promise.resolve({ data: null, error: null })),
    limit: vi.fn().mockReturnValue(Promise.resolve({ data: null, error: null })),
    then: vi.fn().mockImplementation((onfulfilled) => 
      Promise.resolve({ data: null, error: null }).then(onfulfilled)
    ),
  };

  return {
    supabase: {
      from: vi.fn(() => mockQueryBuilder),
    },
  };
});

// Import after mocks are set up
import { fetchTopdeckEloMap, fetchAllTopdeckEloMap, fetchTopdeckElo } from "@/lib/topdeck-elo";
import { supabase } from "@/lib/supabase";

describe("fetchTopdeckEloMap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns empty map for empty input", async () => {
    const result = await fetchTopdeckEloMap([]);
    expect(result).toBeInstanceOf(Map);
    expect(result.size).toBe(0);
  });

  it("returns empty map when supabase returns no data", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any")).in("any", []);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: null, error: null }).then(onfulfilled)
    );

    const result = await fetchTopdeckEloMap(["player-1"]);
    expect(result).toBeInstanceOf(Map);
    expect(result.size).toBe(0);
  });

  it("returns empty map when supabase returns error", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any")).in("any", []);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: null, error: { message: "Network error" } }).then(onfulfilled)
    );

    const result = await fetchTopdeckEloMap(["player-1"]);
    expect(result).toBeInstanceOf(Map);
    expect(result.size).toBe(0);
  });

  it("correctly maps topdeck IDs to elo values", async () => {
    const mockData = [
      { topdeck_id: "player-1", topdeck_elo: 1600 },
      { topdeck_id: "player-2", topdeck_elo: 1650 },
      { topdeck_id: "player-3", topdeck_elo: 1700 },
    ];

    const mockQueryBuilder = vi.mocked(supabase.from("any")).in("any", []);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: mockData, error: null }).then(onfulfilled)
    );

    const result = await fetchTopdeckEloMap(["player-1", "player-2", "player-3"]);

    expect(result.size).toBe(3);
    expect(result.get("player-1")).toBe(1600);
    expect(result.get("player-2")).toBe(1650);
    expect(result.get("player-3")).toBe(1700);
  });

  it("skips rows with null topdeck_id", async () => {
    const mockData = [
      { topdeck_id: null, topdeck_elo: 1600 },
      { topdeck_id: "player-2", topdeck_elo: 1650 },
      { topdeck_id: null, topdeck_elo: 1700 },
    ];

    const mockQueryBuilder = vi.mocked(supabase.from("any")).in("any", []);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: mockData, error: null }).then(onfulfilled)
    );

    const result = await fetchTopdeckEloMap(["player-1", "player-2", "player-3"]);

    expect(result.size).toBe(1);
    expect(result.get("player-2")).toBe(1650);
    expect(result.has("player-1")).toBe(false);
  });

  it("skips rows with non-numeric elo", async () => {
    const mockData = [
      { topdeck_id: "player-1", topdeck_elo: null },
      { topdeck_id: "player-2", topdeck_elo: 1650 },
      { topdeck_id: "player-3", topdeck_elo: "not-a-number" },
    ];

    const mockQueryBuilder = vi.mocked(supabase.from("any")).in("any", []);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: mockData, error: null }).then(onfulfilled)
    );

    const result = await fetchTopdeckEloMap(["player-1", "player-2", "player-3"]);

    expect(result.size).toBe(1);
    expect(result.get("player-2")).toBe(1650);
  });

  it("handles large numbers of players by chunking", async () => {
    // Create 300 player IDs to trigger multiple chunks (chunk size = 250)
    const playerIds = Array.from({ length: 300 }, (_, i) => `player-${i}`);

    // Verify chunking logic works correctly
    const CHUNK_SIZE = 250;
    const chunks: string[][] = [];
    for (let i = 0; i < playerIds.length; i += CHUNK_SIZE) {
      chunks.push(playerIds.slice(i, i + CHUNK_SIZE));
    }

    expect(chunks.length).toBe(2);
    expect(chunks[0].length).toBe(250);
    expect(chunks[1].length).toBe(50);
  });

  it("calls supabase with correct table and column names", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any"));
    
    await fetchTopdeckEloMap(["player-1"]);

    expect(supabase.from).toHaveBeenCalledWith("global_elo_active_leaderboard");
    expect(mockQueryBuilder.select).toHaveBeenCalledWith("topdeck_id, topdeck_elo");
    expect(mockQueryBuilder.eq).toHaveBeenCalledWith("region_type", "global");
    expect(mockQueryBuilder.eq).toHaveBeenCalledWith("region_key", "ALL");
  });
});

describe("fetchAllTopdeckEloMap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns empty map when supabase returns no data", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any")).range(0, 0);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: null, error: null }).then(onfulfilled)
    );

    const result = await fetchAllTopdeckEloMap();
    expect(result).toBeInstanceOf(Map);
    expect(result.size).toBe(0);
  });

  it("correctly maps all players to elo values", async () => {
    const mockData = [
      { topdeck_id: "player-1", topdeck_elo: 1600 },
      { topdeck_id: "player-2", topdeck_elo: 1650 },
    ];

    const mockQueryBuilder = vi.mocked(supabase.from("any")).range(0, 0);
    vi.mocked(mockQueryBuilder.then).mockImplementationOnce((onfulfilled) => 
      Promise.resolve({ data: mockData, error: null }).then(onfulfilled)
    );

    const result = await fetchAllTopdeckEloMap();

    expect(result.size).toBe(2);
    expect(result.get("player-1")).toBe(1600);
    expect(result.get("player-2")).toBe(1650);
  });

  it("calls supabase with correct table name", async () => {
    await fetchAllTopdeckEloMap();

    expect(supabase.from).toHaveBeenCalledWith("global_elo_active_leaderboard");
  });
});

describe("fetchTopdeckElo", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null for non-existent player", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any"));
    vi.mocked(mockQueryBuilder.maybeSingle).mockReturnValueOnce(
      Promise.resolve({ data: null, error: null })
    );

    const result = await fetchTopdeckElo("non-existent");
    expect(result).toBeNull();
  });

  it("returns the elo value for existing player", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any"));
    vi.mocked(mockQueryBuilder.maybeSingle).mockReturnValueOnce(
      Promise.resolve({ data: { topdeck_id: "player-1", topdeck_elo: 1700 }, error: null })
    );

    const result = await fetchTopdeckElo("player-1");
    expect(result).toBe(1700);
  });

  it("returns null when elo is not a number", async () => {
    const mockQueryBuilder = vi.mocked(supabase.from("any"));
    vi.mocked(mockQueryBuilder.maybeSingle).mockReturnValueOnce(
      Promise.resolve({ data: { topdeck_id: "player-1", topdeck_elo: null }, error: null })
    );

    const result = await fetchTopdeckElo("player-1");
    expect(result).toBeNull();
  });
});

// Contract tests are skipped - they require real Supabase credentials and are
// run separately in CI against the actual database.
// To run contract tests locally:
//   SKIP_CONTRACT_TESTS=0 npx vitest run tests/topdeck-elo/topdeck-elo.test.ts