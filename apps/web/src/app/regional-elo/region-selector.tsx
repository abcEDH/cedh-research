"use client";

import { useState } from "react";

type RegionOption = {
  region_key: string;
  player_count: number;
};

export function RegionSelector({
  regions,
  selectedRegion,
}: {
  regions: RegionOption[];
  selectedRegion?: string;
}) {
  const [isLoading, setIsLoading] = useState(false);

  return (
    <form
      action="/regional-elo"
      method="get"
      className="space-y-3"
      onSubmit={() => setIsLoading(true)}
    >
      <label className="text-sm text-muted-foreground">Select a state</label>
      <select name="region" defaultValue={selectedRegion} className="knd-input">
        {regions.map((region) => (
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
        {isLoading ? "Loading region..." : "Load region"}
      </button>
    </form>
  );
}
