import Link from "next/link";
import { normalizeDisplayString } from "@/lib/utils";
import { ColorBadge } from "@/components/ui/color-badge";

export interface HomeCommander {
  commander_id: string;
  commander_name: string;
  avg_win_rate: number;
  total_entries: number;
  color_identity: string[] | null;
  meta_share_pct?: number;
}

export interface HomeRisingCommander extends HomeCommander {
  meta_share_delta: number;
  recent_entries: number;
  prior_entries: number;
}

export function CommanderRow({
  commander,
  rank,
}: {
  commander: HomeCommander;
  rank: number;
}) {
  const winRate = (commander.avg_win_rate * 100).toFixed(1);
  const isAboveExpected = commander.avg_win_rate > 0.25;

  return (
    <Link
      href={`/commanders/${commander.commander_id}`}
      className="flex w-full min-w-0 items-start gap-3 rounded-lg border border-border/60 bg-muted/30 px-3 py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <span className="shrink-0 pt-0.5 font-mono text-xs text-muted-foreground">#{rank}</span>
      <div className="flex shrink-0 flex-wrap gap-1 pt-0.5">
        {commander.color_identity?.filter(Boolean).map((color) => (
          <ColorBadge key={color} color={color} />
        ))}
      </div>
      <div className="min-w-0 flex-1">
        <p className="break-words text-sm font-medium text-foreground">
          {normalizeDisplayString(commander.commander_name)}
        </p>
        <p className="break-words text-xs text-muted-foreground">
          {commander.total_entries} entries
          {commander.meta_share_pct != null && (
            <> · {commander.meta_share_pct.toFixed(1)}% meta</>
          )}
        </p>
      </div>
      <div className="shrink-0 self-start text-right">
        <p className={`font-mono text-sm ${isAboveExpected ? "text-primary" : "text-muted-foreground"}`}>
          {winRate}%
        </p>
        <p className="text-xs text-muted-foreground">win rate</p>
      </div>
    </Link>
  );
}

export function RisingCommanderRow({
  commander,
  rank,
}: {
  commander: HomeRisingCommander;
  rank: number;
}) {
  const winRate = (commander.avg_win_rate * 100).toFixed(1);
  const isAboveExpected = commander.avg_win_rate > 0.25;

  return (
    <Link
      href={`/commanders/${commander.commander_id}`}
      className="flex w-full min-w-0 items-start gap-3 rounded-lg border border-border/60 bg-muted/30 px-3 py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <span className="shrink-0 pt-0.5 font-mono text-xs text-muted-foreground">#{rank}</span>
      <div className="flex shrink-0 flex-wrap gap-1 pt-0.5">
        {commander.color_identity?.filter(Boolean).map((color) => (
          <ColorBadge key={color} color={color} />
        ))}
      </div>
      <div className="min-w-0 flex-1">
        <p className="break-words text-sm font-medium text-foreground">
          {normalizeDisplayString(commander.commander_name)}
        </p>
        <p className="break-words text-xs text-muted-foreground">
          {commander.recent_entries} latest stretch · prior {commander.prior_entries} ·{" "}
          <span className={isAboveExpected ? "text-primary" : undefined}>{winRate}%</span> win
          {commander.meta_share_pct != null && (
            <> · {commander.meta_share_pct.toFixed(1)}% meta</>
          )}
        </p>
      </div>
      <div className="shrink-0 self-start text-right">
        <p className="font-mono text-sm text-primary">
          +{(commander.meta_share_delta * 100).toFixed(2)}%
        </p>
        <p className="text-xs text-muted-foreground">meta share</p>
      </div>
    </Link>
  );
}
