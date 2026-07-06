import { describe, expect, it } from "vitest";
import { resolveTenantSlug } from "@/lib/games/resolve-tenant";
import { DEFAULT_GAME } from "@/lib/games/registry";

describe("resolveTenantSlug", () => {
  it("passes through paths already prefixed with a valid game slug", () => {
    expect(
      resolveTenantSlug({ pathname: "/riftbound", queryGame: null, host: "gundam.tedh.gg" })
    ).toBeNull();
    expect(
      resolveTenantSlug({ pathname: "/retro/tournaments/abc", queryGame: null, host: null })
    ).toBeNull();
  });

  it("prefers the ?game= query override over the hostname", () => {
    expect(
      resolveTenantSlug({ pathname: "/", queryGame: "gundam", host: "riftbound.tedh.gg" })
    ).toBe("gundam");
  });

  it("ignores junk ?game= values", () => {
    expect(
      resolveTenantSlug({ pathname: "/", queryGame: "magic", host: "riftbound.tedh.gg" })
    ).toBe("riftbound");
    expect(resolveTenantSlug({ pathname: "/", queryGame: "toString", host: "" })).toBe(
      DEFAULT_GAME
    );
  });

  it("resolves the tenant from the first hostname label", () => {
    expect(resolveTenantSlug({ pathname: "/", queryGame: null, host: "riftbound.tedh.gg" })).toBe(
      "riftbound"
    );
    expect(resolveTenantSlug({ pathname: "/tournaments", queryGame: null, host: "gundam.tedh.gg" })).toBe(
      "gundam"
    );
  });

  it("handles localhost subdomains with ports", () => {
    expect(
      resolveTenantSlug({ pathname: "/", queryGame: null, host: "retro.localhost:3000" })
    ).toBe("retro");
  });

  it("falls back to the default game for unknown hosts", () => {
    expect(resolveTenantSlug({ pathname: "/", queryGame: null, host: "localhost:3000" })).toBe(
      DEFAULT_GAME
    );
    expect(resolveTenantSlug({ pathname: "/", queryGame: null, host: "tedh.gg" })).toBe(
      DEFAULT_GAME
    );
    expect(resolveTenantSlug({ pathname: "/", queryGame: null, host: null })).toBe(DEFAULT_GAME);
  });
});
