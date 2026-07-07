import { describe, expect, it } from "vitest";
import { withGameParam } from "@/lib/games/links";

describe("withGameParam", () => {
  it("appends the game slug to a bare path", () => {
    expect(withGameParam("/", "riftbound")).toBe("/?game=riftbound");
    expect(withGameParam("/tournaments", "gundam")).toBe("/tournaments?game=gundam");
  });

  it("merges extra params alongside the game slug", () => {
    expect(withGameParam("/tournaments", "retro", { format: "goat" })).toBe(
      "/tournaments?game=retro&format=goat"
    );
  });

  it("preserves an existing query string on the path", () => {
    const href = withGameParam("/tournaments?format=edison", "retro");
    const params = new URLSearchParams(href.split("?")[1]);
    expect(params.get("format")).toBe("edison");
    expect(params.get("game")).toBe("retro");
  });

  it("overrides a stale game param already present on the path", () => {
    const href = withGameParam("/?game=gundam", "riftbound");
    const params = new URLSearchParams(href.split("?")[1]);
    expect(params.get("game")).toBe("riftbound");
  });
});
