import { describe, expect, it } from "vitest";

import { greet } from "../index";

describe("greet", () => {
  it("exposes formatted greetings through the package entry point", () => {
    expect(greet("  cEDH  ")).toBe("Hello, cEDH!");
  });
});
