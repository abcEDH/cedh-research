/**
 * Card image providers — resolve a card in a decklist to an image URL and/or
 * an external reference URL. Which provider a tenant uses is declared in the
 * game registry (`GameConfig.cardImages`).
 */

export interface CardImageProvider {
  imageUrl(card: { name: string; externalId?: string }): string | null;
  externalUrl(card: { name: string }): string | null;
}

export const noneProvider: CardImageProvider = {
  imageUrl: () => null,
  externalUrl: () => null,
};

export const ygoprodeckProvider: CardImageProvider = {
  imageUrl: (card) =>
    card.externalId ? `https://images.ygoprodeck.com/images/cards/${card.externalId}.jpg` : null,
  externalUrl: (card) =>
    `https://ygoprodeck.com/card/?search=${encodeURIComponent(card.name)}`,
};

const PROVIDERS: Record<"none" | "ygoprodeck", CardImageProvider> = {
  none: noneProvider,
  ygoprodeck: ygoprodeckProvider,
};

export function getCardImageProvider(kind: "none" | "ygoprodeck"): CardImageProvider {
  return PROVIDERS[kind];
}
