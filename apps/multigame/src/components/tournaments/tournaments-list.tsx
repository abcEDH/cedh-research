import Link from "next/link";
import type { TournamentRow } from "@/lib/schemas/api-contracts";
import { formatDate } from "@/lib/tournaments/stats";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function TournamentsList({ tournaments }: { tournaments: TournamentRow[] }) {
  if (tournaments.length === 0) {
    return (
      <p className="rounded-xl border border-border/70 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
        No tournaments yet. Events appear once tournament data has been ingested.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Tournament</TableHead>
          <TableHead>Date</TableHead>
          <TableHead className="text-right">Players</TableHead>
          <TableHead>Format</TableHead>
          <TableHead className="text-right">Top cut</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tournaments.map((tournament) => (
          <TableRow key={tournament.id}>
            <TableCell className="font-medium">
              <Link
                href={`/tournaments/${tournament.topdeck_tid}`}
                className="transition hover:text-primary"
              >
                {tournament.name}
              </Link>
            </TableCell>
            <TableCell>{formatDate(tournament.start_date)}</TableCell>
            <TableCell className="text-right">{tournament.player_count}</TableCell>
            <TableCell>{tournament.format}</TableCell>
            <TableCell className="text-right">{tournament.top_cut ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
