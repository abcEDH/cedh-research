import { describe, expect, it } from "vitest";
import {
  getCardImageProvider,
  noneProvider,
  ygoprodeckProvider,
} from "@/lib/games/card-images";

describe("card image providers", () => {
  it("noneProvider returns null for everything", () => {
    expect(noneProvider.imageUrl({ name: "Any Card", externalId: "123" })).toBeNull();
    expect(noneProvider.externalUrl({ name: "Any Card" })).toBeNull();
  });

  it("ygoprodeckProvider builds image URLs from the external id", () => {
    expect(ygoprodeckProvider.imageUrl({ name: "Dark Magician", externalId: "46986414" })).toBe(
      "https://images.ygoprodeck.com/images/cards/46986414.jpg"
    );
  });

  it("ygoprodeckProvider returns null image URL without an external id", () => {
    expect(ygoprodeckProvider.imageUrl({ name: "Dark Magician" })).toBeNull();
  });

  it("ygoprodeckProvider builds encoded external search URLs", () => {
    expect(ygoprodeckProvider.externalUrl({ name: "Pot of Greed & Co" })).toBe(
      "https://ygoprodeck.com/card/?search=Pot%20of%20Greed%20%26%20Co"
    );
  });

  it("getCardImageProvider maps registry kinds to providers", () => {
    expect(getCardImageProvider("none")).toBe(noneProvider);
    expect(getCardImageProvider("ygoprodeck")).toBe(ygoprodeckProvider);
  });
});
