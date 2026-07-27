import { describe, expect, it } from "vitest";

import { parseContentDispositionFilename } from "@/components/analytics/player-matchups-export";

describe("parseContentDispositionFilename", () => {
  it("prefers and decodes the RFC 5987 filename", () => {
    expect(
      parseContentDispositionFilename(
        'attachment; filename="fallback.json"; filename*=UTF-8\'\'%E3%83%97%E3%83%AC%E3%82%A4.json',
        "default.json"
      )
    ).toBe("プレイ.json");
  });

  it("parses the plain filename without including other parameters", () => {
    expect(
      parseContentDispositionFilename(
        'attachment; filename="player.json"; filename*=UTF-8\'\'player.json',
        "default.json"
      )
    ).toBe("player.json");
  });
});
