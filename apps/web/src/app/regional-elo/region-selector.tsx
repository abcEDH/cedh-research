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
  const countryRegions = regions.filter((region) => region.region_type === "country");
  const [view, setView] = useState(
    supportsCountryRegions && selectedScope === "country" && selectedCountry
      ? selectedCountry
      : "global"
  );
  const [region, setRegion] = useState(selectedRegion ?? "");
  const country = view === "global" ? "" : view;
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
      <label className="text-sm text-muted-foreground">Country</label>
      <select
        value={view}
        className="knd-input"
        onChange={(event) => {
          setView(event.target.value);
          setRegion("");
        }}
      >
        <option value="global">GLOBAL</option>
        {supportsCountryRegions
          ? countryRegions.map((region) => (
              <option key={region.region_key} value={region.region_key}>
                {region.region_key}
              </option>
            ))
          : null}
      </select>

      <input type="hidden" name="scope" value={view === "global" ? "global" : "country"} />
      {view !== "global" ? <input type="hidden" name="country" value={view} /> : null}

      {view !== "global" ? (
        <>
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
                {region.region_key}
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
