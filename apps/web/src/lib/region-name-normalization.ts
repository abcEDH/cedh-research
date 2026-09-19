import regions from "../../../../packages/backend/data/region_aliases.json";

const countryAliases: Record<string, string> = {
  US: "UNITED STATES", USA: "UNITED STATES", "U.S.": "UNITED STATES",
  "UNITED STATES OF AMERICA": "UNITED STATES", CA: "CANADA", CAN: "CANADA",
  AU: "AUSTRALIA", AUS: "AUSTRALIA", GB: "UNITED KINGDOM", GBR: "UNITED KINGDOM", UK: "UNITED KINGDOM",
};

/** Resolve old bookmarked abbreviations; stored names are normalized by Postgres. */
export function canonicalRegionKey(value: string, country?: string | null): string {
  const key = value.trim().toUpperCase();
  const rawCountry = (country ?? "").trim().toUpperCase();
  const countryKey = countryAliases[rawCountry] ?? rawCountry;
  const matches = new Set(regions.filter((region) =>
    (!countryKey || region.country === countryKey) &&
    [region.name, ...region.aliases].some((alias) => alias.toUpperCase() === key)
  ).map((region) => region.name.toUpperCase()));
  return matches.size === 1 ? [...matches][0] : key;
}
