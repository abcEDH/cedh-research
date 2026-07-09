import type { DeckIdentityStatRow } from "@/lib/schemas/api-contracts";
import { computeMetaShare, formatPercent, formatWinRate } from "@/lib/archetypes/stats";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function ArchetypeStatsTable({
  rows,
  identityNoun,
}: {
  rows: DeckIdentityStatRow[];
  identityNoun: string;
}) {
  if (rows.length === 0) {
    return (
      <p className="rounded-xl border border-border/70 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
        No results yet. Stats appear once tournament data has been ingested.
      </p>
    );
  }

  const withShare = computeMetaShare(rows);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{identityNoun}</TableHead>
          <TableHead className="text-right">Entries</TableHead>
          <TableHead className="text-right">Meta share</TableHead>
          <TableHead className="text-right">W-L-D</TableHead>
          <TableHead className="text-right">Top cuts</TableHead>
          <TableHead className="text-right">Avg win rate</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {withShare.map((row) => (
          <TableRow key={row.identity_id}>
            <TableCell className="font-medium">{row.name}</TableCell>
            <TableCell className="text-right">{row.entries}</TableCell>
            <TableCell className="text-right">{formatPercent(row.metaShare)}</TableCell>
            <TableCell className="text-right">
              {row.wins}-{row.losses}-{row.draws}
            </TableCell>
            <TableCell className="text-right">{row.top_cut_count}</TableCell>
            <TableCell className="text-right">{formatWinRate(row.avg_win_rate)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
