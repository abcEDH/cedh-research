import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CommanderMomentum, MomentumPeriod } from "@/lib/commanders/fetchers";

function DeltaValue({ changeValue, suffix }: { changeValue: number | null; suffix: string }) {
  if (changeValue === null) {
    return <span className="font-mono text-muted-foreground">New</span>;
  }

  if (changeValue === 0) {
    return <span className="font-mono text-muted-foreground">±0{suffix}</span>;
  }

  const isUp = changeValue > 0;
  const toneClass = isUp ? "text-primary" : "text-[hsl(var(--knd-amber))]";

  return (
    <span className={`font-mono font-semibold ${toneClass}`}>
      {isUp ? "▲" : "▼"} {Math.abs(changeValue).toFixed(1)}
      {suffix}
    </span>
  );
}

function MomentumRow({ period }: { period: MomentumPeriod | null }) {
  if (!period) {
    return (
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">No completed period yet</p>
        <p className="text-muted-foreground">Not enough recorded games to show momentum.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{period.label}</p>
      <div className="flex justify-between items-center">
        <span className="text-muted-foreground">Entries</span>
        <span className="flex items-center gap-2">
          <span className="font-mono text-foreground">{period.entries.toLocaleString()}</span>
          <DeltaValue changeValue={period.entriesChangePct} suffix="%" />
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-muted-foreground">Win Rate</span>
        <span className="flex items-center gap-2">
          <span className="font-mono text-foreground">{(period.winRate * 100).toFixed(1)}%</span>
          <DeltaValue changeValue={period.winRateChangePp} suffix="pp" />
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
          How this commander&apos;s entries and win rate compare to the prior fully completed period. In-progress
          weeks/months are excluded so partial data isn&apos;t compared against a full prior period.
        </p>
      </CardHeader>
      <CardContent className="grid gap-6 text-sm sm:grid-cols-2">
        <MomentumRow period={momentum.week} />
        <MomentumRow period={momentum.month} />
      </CardContent>
    </Card>
  );
}
