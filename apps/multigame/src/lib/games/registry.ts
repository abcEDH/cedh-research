/**
 * Game registry — single source of per-tenant behavior for the multigame app.
 *
 * Each tenant (subdomain) maps to one GameConfig. The `dbGame` / `dbFormat`
 * strings must match the discriminator columns written by backend ingestion
 * (see docs/decisions/0015-multi-game-single-schema.md).
 */

export type GameSlug = "riftbound" | "gundam" | "retro";

export interface GameFormat {
  slug: string;
  name: string;
  /** Exact tournaments.format string; null = no format filter (game-wide). */
  dbFormat: string | null;
}

export interface GameConfig {
  slug: GameSlug;
  name: string;
  tagline: string;
  hostname: string;
  baseUrl: string;
  /** Exact tournaments.game string. */
  dbGame: string;
  formats: GameFormat[];
  /** Format slug used when no ?format= is present. */
  defaultFormat: string;
  identityNoun: string;
  cardImages: "none" | "ygoprodeck";
  externalLinks: { label: string; href: string }[];
  compliance: { fanContentNotice: string; copyrightHolder: string };
}

const GAMES: Record<GameSlug, GameConfig> = {
  riftbound: {
    slug: "riftbound",
    name: "Riftbound",
    tagline: "Riftbound tournament meta, Legends, and results from TopDeck.gg events.",
    hostname: "riftbound.tedh.gg",
    baseUrl: "https://riftbound.tedh.gg",
    dbGame: "Riftbound",
    formats: [{ slug: "all", name: "All formats", dbFormat: null }],
    defaultFormat: "all",
    identityNoun: "Legend",
    cardImages: "none",
    externalLinks: [{ label: "TopDeck.gg Riftbound", href: "https://topdeck.gg" }],
    compliance: {
      fanContentNotice:
        "This site is unofficial Fan Content. Not approved or endorsed by Riot Games. Portions of the materials used are property of Riot Games. Riftbound © Riot Games.",
      copyrightHolder: "Riot Games",
    },
  },
  gundam: {
    slug: "gundam",
    name: "Gundam Card Game",
    tagline: "Gundam Card Game tournament meta, decks, and results from TopDeck.gg events.",
    hostname: "gundam.tedh.gg",
    baseUrl: "https://gundam.tedh.gg",
    dbGame: "Gundam TCG",
    formats: [{ slug: "all", name: "All formats", dbFormat: null }],
    defaultFormat: "all",
    identityNoun: "Deck",
    cardImages: "none",
    externalLinks: [],
    compliance: {
      fanContentNotice:
        "This site is unofficial Fan Content, not affiliated with or endorsed by BANDAI. Gundam and all associated properties © SOTSU / SUNRISE / BANDAI.",
      copyrightHolder: "BANDAI",
    },
  },
  retro: {
    slug: "retro",
    name: "Yu-Gi-Oh Retro",
    tagline: "Yu-Gi-Oh retro format (Edison, GOAT) tournament meta and results from TopDeck.gg events.",
    hostname: "retro.tedh.gg",
    baseUrl: "https://retro.tedh.gg",
    dbGame: "Yu-Gi-Oh",
    // PROVISIONAL: these dbFormat strings are unverified against live TopDeck
    // data. After the first ingestion run, pin them from
    // `SELECT DISTINCT format FROM tournaments WHERE game = 'Yu-Gi-Oh'`
    // (see docs/decisions/0015-multi-game-single-schema.md appendix).
    formats: [
      { slug: "edison", name: "Edison", dbFormat: "Edison" },
      { slug: "goat", name: "GOAT", dbFormat: "Goat" },
    ],
    defaultFormat: "edison",
    identityNoun: "Archetype",
    cardImages: "ygoprodeck",
    externalLinks: [],
    compliance: {
      fanContentNotice:
        "This site is unofficial Fan Content, not affiliated with or endorsed by Konami. Yu-Gi-Oh! © Konami Digital Entertainment.",
      copyrightHolder: "Konami Digital Entertainment",
    },
  },
};

export const GAME_SLUGS = Object.keys(GAMES) as GameSlug[];

export function isGameSlug(value: unknown): value is GameSlug {
  // Object.hasOwn (not `in`) so prototype keys like "toString" are rejected.
  return typeof value === "string" && Object.hasOwn(GAMES, value);
}

const envDefault = process.env.NEXT_PUBLIC_DEFAULT_GAME;

export const DEFAULT_GAME: GameSlug = isGameSlug(envDefault) ? envDefault : "riftbound";

export function getGame(slug: string): GameConfig | null {
  return isGameSlug(slug) ? GAMES[slug] : null;
}

/**
 * Resolve a `?format=` slug against a game's formats, falling back to the
 * game's default format for unknown or absent slugs.
 */
export function resolveFormat(game: GameConfig, formatSlug: string | undefined): GameFormat {
  const match = game.formats.find((format) => format.slug === formatSlug);
  if (match) {
    return match;
  }
  const fallback = game.formats.find((format) => format.slug === game.defaultFormat);
  return fallback ?? game.formats[0];
}
