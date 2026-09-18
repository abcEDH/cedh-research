import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CommanderTrendTableRow } from "@/lib/commanders/fetchers";

function SnapshotTable({
  rows,
  title,
  periodLabel,
}: {
  rows: CommanderTrendTableRow[];
  title: string;
  periodLabel: string;
}) {
  return (
    <Card>
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <TableHead>{periodLabel}</TableHead>
              <TableHead className="text-right">Entries</TableHead>
              <TableHead className="text-right">Win %</TableHead>
              <TableHead className="text-right">Pts/Game</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.period} className="border-border/60">
                <TableCell className="font-mono text-xs text-muted-foreground">{row.period}</TableCell>
                <TableCell className="text-right font-mono">{row.entries}</TableCell>
                <TableCell className="text-right font-mono text-muted-foreground">
                  {row.winRate.toFixed(1)}%
                </TableCell>
                <TableCell className="text-right font-mono text-muted-foreground">
                  {row.pointsPerGame.toFixed(2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export function TrendSnapshotTables({
  weeklyTable,
  monthlyTable,
}: {
  weeklyTable: CommanderTrendTableRow[];
  monthlyTable: CommanderTrendTableRow[];
}) {
  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <SnapshotTable rows={weeklyTable} title="Weekly snapshot" periodLabel="Week" />
      <SnapshotTable rows={monthlyTable} title="Monthly snapshot" periodLabel="Month" />
    </div>
  );
}
