"use client";

import { useState } from "react";

type RegionOption = {
  region_type: string;
  region_key: string;
  country_key: string | null;
  player_count: number;
};

export function RegionSelector({
  regions,
  selectedScope,
  selectedCountry,
  selectedRegion,
  supportsCountryRegions = true,
}: {
  regions: RegionOption[];
  selectedScope: "global" | "country";
  selectedCountry?: string;
  selectedRegion?: string;
  supportsCountryRegions?: boolean;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const globalRegion = regions.find((region) => region.region_type === "global");
  const countryRegions = regions.filter((region) => region.region_type === "country");
  const [scope, setScope] = useState(supportsCountryRegions ? selectedScope : "global");
  const [country, setCountry] = useState(selectedCountry ?? countryRegions[0]?.region_key ?? "");
  const [region, setRegion] = useState(selectedRegion ?? "");
  const stateRegions = regions.filter(
    (region) => region.region_type === "state" && region.country_key === country
  );

  return (
    <form
      action="/regional-elo"
      method="get"
      className="space-y-3"
      onSubmit={() => setIsLoading(true)}
    >
      <label className="text-sm text-muted-foreground">View</label>
      <select
        name="scope"
        value={scope}
        className="knd-input"
        onChange={(event) => setScope(event.target.value === "country" ? "country" : "global")}
      >
        <option value="global">
          Global {globalRegion ? `(${globalRegion.player_count})` : ""}
        </option>
        {supportsCountryRegions ? <option value="country">Country</option> : null}
      </select>

      {scope === "country" ? (
        <>
          <label className="text-sm text-muted-foreground">Country</label>
          <select
            name="country"
            value={country}
            className="knd-input"
            onChange={(event) => {
              setCountry(event.target.value);
              setRegion("");
            }}
          >
            {countryRegions.map((region) => (
              <option key={region.region_key} value={region.region_key}>
                {region.region_key} ({region.player_count})
              </option>
            ))}
          </select>

          <label className="text-sm text-muted-foreground">State</label>
          <select
            name="region"
            value={region}
            className="knd-input"
            onChange={(event) => setRegion(event.target.value)}
          >
            <option value="">All states</option>
            {stateRegions.map((region) => (
              <option key={`${region.country_key}:${region.region_key}`} value={region.region_key}>
                {region.region_key} ({region.player_count})
              </option>
            ))}
          </select>
        </>
      ) : null}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background disabled:opacity-70"
      >
        {isLoading ? "Loading leaderboard..." : "Load leaderboard"}
      </button>
    </form>
  );
}
