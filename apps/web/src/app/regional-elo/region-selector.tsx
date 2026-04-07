"use client";

import { useState } from "react";

type RegionOption = {
  region_type: string;
  region_key: string;
  player_count: number;
};

export function RegionSelector({
  regions,
  selectedScope,
  selectedRegion,
}: {
  regions: RegionOption[];
  selectedScope: "global" | "state";
  selectedRegion?: string;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const globalRegion = regions.find((region) => region.region_type === "global");
  const stateRegions = regions.filter((region) => region.region_type === "state");

  return (
    <form
      action="/regional-elo"
      method="get"
      className="space-y-3"
      onSubmit={() => setIsLoading(true)}
    >
      <label className="text-sm text-muted-foreground">View</label>
      <select name="scope" defaultValue={selectedScope} className="knd-input">
        <option value="global">
          Global {globalRegion ? `(${globalRegion.player_count})` : ""}
        </option>
        <option value="state">By state assignment</option>
      </select>

      <label className="text-sm text-muted-foreground">State</label>
      <select name="region" defaultValue={selectedRegion} className="knd-input">
        {stateRegions.map((region) => (
          <option key={region.region_key} value={region.region_key}>
            {region.region_key} ({region.player_count})
          </option>
        ))}
      </select>
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
