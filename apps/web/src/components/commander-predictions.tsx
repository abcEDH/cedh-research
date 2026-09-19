import { commanderPredictionRows, type PlayerCommanderProfileRow } from "@/lib/commander-predictions";

function known(value: string | null | undefined) {
  return value?.trim() && value.trim().toLowerCase() !== "unknown commander" ? value : null;
}

export function CommanderPredictions({ profile }: { profile: PlayerCommanderProfileRow | null }) {
  const rows = commanderPredictionRows(profile);
  const active = known(profile?.active_commander);
  const latest = known(profile?.latest_commander);
  const activeShare = rows.find((row) => row.commander === active)?.share;
  if (!active && !latest && !rows.length) return null;
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
  return (
    <div className="mb-4 rounded-md border border-border/60 p-3 text-xs text-muted-foreground">
      <div className="grid gap-3 md:grid-cols-3">
        <div>
          <div className="uppercase tracking-[0.16em]">Predicted Active</div>
          <div className="mt-1 font-medium text-foreground">{active ?? "Unknown"}</div>
          {activeShare != null ? <div className="mt-1">{percent(activeShare)} modeled share</div> : null}
        </div>
        <div>
          <div className="uppercase tracking-[0.16em]">Latest Commander</div>
          <div className="mt-1 font-medium text-foreground">{latest ?? "Unknown"}</div>
          {profile?.latest_commander_date ? <div className="mt-1">{new Date(profile.latest_commander_date).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })}</div> : null}
        </div>
        <div>
          <div className="uppercase tracking-[0.16em]">Top Predictions</div>
          <div className="mt-1 space-y-1">
            {rows.length ? rows.map((row) => (
              <div key={row.commander} className="flex justify-between gap-3">
                <span className="min-w-0 truncate text-foreground">{row.commander}</span>
                <span className="font-mono">{row.share == null ? "—" : percent(row.share)}</span>
              </div>
            )) : "Unknown"}
          </div>
        </div>
      </div>
      <p className="mt-3">Modeled commander choices based on past events. Only the top three are shown, so their shares may total less than 100%.</p>
    </div>
  );
}
