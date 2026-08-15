import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CommanderMomentum } from "@/lib/commanders/fetchers";

function DeltaValue({ changePct, suffix }: { changePct: string | null; suffix: string }) {
  if (changePct === null) {
    return <span className="font-mono text-muted-foreground">New</span>;
  }

  const value = parseFloat(changePct);
  if (Number.isNaN(value) || value === 0) {
    return <span className="font-mono text-muted-foreground">±0{suffix}</span>;
  }

  const isUp = value > 0;
  const toneClass = isUp ? "text-primary" : "text-[hsl(var(--knd-amber))]";

  return (
    <span className={`font-mono font-semibold ${toneClass}`}>
      {isUp ? "▲" : "▼"} {Math.abs(value).toFixed(1)}
      {suffix}
    </span>
  );
}

function MomentumRow({
  label,
  entries,
  winRate,
  entriesChangePct,
  winRateChangePp,
}: {
  label: string;
  entries: number;
  winRate: string;
  entriesChangePct: string | null;
  winRateChangePp: string | null;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <div className="flex justify-between items-center">
        <span className="text-muted-foreground">Entries</span>
        <span className="flex items-center gap-2">
          <span className="font-mono text-foreground">{entries.toLocaleString()}</span>
          <DeltaValue changePct={entriesChangePct} suffix="%" />
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-muted-foreground">Win Rate</span>
        <span className="flex items-center gap-2">
          <span className="font-mono text-foreground">{(parseFloat(winRate) * 100).toFixed(1)}%</span>
          <DeltaValue changePct={winRateChangePp} suffix="pp" />
        </span>
      </div>
    </div>
  );
}

export function MomentumCard({ momentum }: { momentum: CommanderMomentum }) {
  return (
    <Card>
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">Momentum</CardTitle>
        <p className="text-sm text-muted-foreground">
          How this commander&apos;s entries and win rate are trending versus the prior period.
        </p>
      </CardHeader>
      <CardContent className="grid gap-6 text-sm sm:grid-cols-2">
        <MomentumRow
          label="This Week"
          entries={momentum.week_entries}
          winRate={momentum.week_win_rate}
          entriesChangePct={momentum.week_entries_change_pct}
          winRateChangePp={momentum.week_win_rate_change_pp}
        />
        <MomentumRow
          label="This Month"
          entries={momentum.month_entries}
          winRate={momentum.month_win_rate}
          entriesChangePct={momentum.month_entries_change_pct}
          winRateChangePp={momentum.month_win_rate_change_pp}
        />
      </CardContent>
    </Card>
  );
}
