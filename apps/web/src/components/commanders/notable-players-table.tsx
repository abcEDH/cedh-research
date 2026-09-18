import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { normalizeDisplayString } from "@/lib/utils";
import type { NotablePlayer } from "@/lib/commanders/fetchers";

export function NotablePlayersTable({
  players,
  commanderName,
}: {
  players: NotablePlayer[];
  commanderName: string;
}) {
  return (
    <Card>
      <CardHeader className="knd-panel-header">
        <CardTitle className="text-lg">
          Notable {normalizeDisplayString(commanderName)} Players
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Players with 2+ tournament entries using this commander.
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <TableHead>Player</TableHead>
              <TableHead className="text-right">Entries</TableHead>
              <TableHead className="text-right">Games</TableHead>
              <TableHead className="text-right">Win Rate</TableHead>
              <TableHead className="text-right">Top 16/Top 4s</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {players.map((player) => (
              <TableRow key={player.player_name} className="border-border/60">
                <TableCell className="font-medium">
                  {player.topdeck_id ? (
                    <a
                      href={`https://topdeck.gg/profile/${player.topdeck_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground hover:text-primary"
                    >
                      {player.player_name}
                      <span className="ml-1 text-muted-foreground text-xs">↗</span>
                    </a>
                  ) : (
                    player.player_name
                  )}
                </TableCell>
                <TableCell className="text-right font-mono text-[hsl(var(--knd-amber))]">
                  {player.entries}
                </TableCell>
                <TableCell className="text-right font-mono text-muted-foreground">
                  {player.total_games}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {player.win_rate ? (
                    <span
                      className={
                        parseFloat(player.win_rate) > 0.25
                          ? "text-primary"
                          : parseFloat(player.win_rate) < 0.2
                            ? "text-[hsl(var(--knd-amber))]"
                            : "text-muted-foreground"
                      }
                    >
                      {(parseFloat(player.win_rate) * 100).toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono text-[hsl(var(--knd-amber))]">
                  {player.top_16_count}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
