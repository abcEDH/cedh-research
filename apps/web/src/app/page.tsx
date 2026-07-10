import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { unstable_cache } from "next/cache";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChevronRight, Trophy } from "lucide-react";
import Link from "next/link";
import { HomeSearchBar } from "@/components/home-search-bar";
import { fetchRecentTournaments, getLeaderboardPreview } from "@/lib/home/fetchers";

const HOME_CACHE_REVALIDATE_SECONDS = 60 * 60 * 6; // 6 hours

export const dynamic = "force-dynamic";

const getCachedRecentTournaments = unstable_cache(
  fetchRecentTournaments,
  ["recent-tournaments"],
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

const getCachedLeaderboardPreview = unstable_cache(
  getLeaderboardPreview,
  ["home-leaderboard-preview-v4"],
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

export default async function Home() {
  const [leaderboardPlayers, recentTournaments] = await Promise.all([
    getCachedLeaderboardPreview(),
    getCachedRecentTournaments().catch((error) => {
      console.error("Home recent tournaments cache refresh failed:", error);
      return [];
    }),
  ]);

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <section className="mt-8 border-b border-border/60 py-12">
          <div className="mx-auto flex max-w-3xl flex-col items-center gap-7 text-center">
            <div className="space-y-5">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-primary">
                LIVE · TopDeck.gg · 12,481 entries
              </div>
              <h2 className="text-4xl font-semibold leading-[1.05] tracking-tight text-foreground md:text-[46px]">
                Competitive intelligence for cEDH.
              </h2>
              <p className="mx-auto max-w-xl text-base leading-7 text-muted-foreground">
                Win rates, tournament results, and commander meta share sourced from tournament records.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Button asChild className="gap-2">
                  <Link href="/tournaments">
                    <Trophy className="h-4 w-4" />
                    Latest Tournaments
                  </Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/regional-elo">Commander Rankings</Link>
                </Button>
              </div>
            </div>
            <HomeSearchBar />
          </div>
        </section>

        <section className="mt-10">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-primary">Results</div>
              <h2 className="text-xl font-semibold">Recent Events</h2>
            </div>
            <Link href="/tournaments" className="text-sm text-primary transition-colors hover:text-foreground">
              View all →
            </Link>
          </div>
          <div className="knd-panel overflow-hidden">
            {recentTournaments.map((event) => (
              <Link
                key={event.slug}
                href={`/tournaments/${event.slug}`}
                className="group flex items-center gap-4 border-b border-border/60 px-4 py-3 transition-colors last:border-b-0 hover:bg-accent/20"
              >
                <DateBlock date={event.date} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold text-foreground">{event.name}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {event.winner} · <span className="font-mono">{event.players.toLocaleString()}</span> players
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-primary/70" />
              </Link>
            ))}
          </div>
        </section>

        <section className="mt-12">
          <Card data-testid="global-leaderboard-card" className="border-primary/20 bg-primary/5">
            <CardHeader className="flex flex-row items-center justify-between pb-3 sm:pb-4">
              <div className="min-w-0 flex-1">
                <CardTitle className="text-base sm:text-lg truncate">Global Leaderboard</CardTitle>
                <p className="text-[10px] sm:text-sm text-muted-foreground truncate">Active players ranked by TopDeck Elo</p>
              </div>
              <Button asChild variant="ghost" size="xs" className="shrink-0 border border-border/70 text-[10px] h-8 px-2 ml-2">
                <Link href="/regional-elo">Full View</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-2 sm:px-6">
              <div className="overflow-x-auto">
                <Table data-testid="global-leaderboard-table">
                  <TableHeader>
                    <TableRow className="border-border/60 text-[10px] uppercase tracking-wider text-muted-foreground">
                      <TableHead className="py-2 px-1 w-8">#</TableHead>
                      <TableHead className="py-2 px-2">Player</TableHead>
                      <TableHead className="py-2 px-2 text-right">Elo</TableHead>
                      <TableHead className="py-2 px-2 hidden sm:table-cell">Commander</TableHead>
                      <TableHead className="py-2 px-2 hidden md:table-cell">Games</TableHead>
                      <TableHead className="py-2 px-2 hidden md:table-cell">W-L-D</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leaderboardPlayers.length > 0 ? (
                      leaderboardPlayers.map((player) => {
                        return (
                          <TableRow key={player.player_id} className="border-border/60">
                            <TableCell className="py-3 px-1 font-mono text-[10px] text-muted-foreground">
                              {player.rank}
                            </TableCell>
                            <TableCell className="py-3 px-2">
                              <Link
                                href={`/regional-elo/player/${player.topdeck_id}`}
                                className="font-medium text-foreground hover:text-primary text-xs sm:text-sm"
                              >
                                {player.player_name}
                              </Link>
                            </TableCell>
                            <TableCell className="py-3 px-2 text-right font-mono text-xs sm:text-sm font-semibold text-primary">
                              {player.topdeck_elo == null ? "—" : Math.round(player.topdeck_elo)}
                            </TableCell>
                            <TableCell className="py-3 px-2 max-w-[180px] text-[10px] text-muted-foreground hidden sm:table-cell">
                              {player.active_commander ? (
                                <span className="line-clamp-1">
                                  {player.active_commander}
                                </span>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                            <TableCell className="py-3 px-2 font-mono text-[10px] text-muted-foreground hidden md:table-cell">
                              {player.games_played.toLocaleString()}
                            </TableCell>
                            <TableCell className="py-3 px-2 font-mono text-[10px] text-muted-foreground hidden md:table-cell">
                              {player.wins}-{player.losses}-{player.draws}
                            </TableCell>
                          </TableRow>
                        );
                      })
                    ) : (
                      <TableRow className="border-border/60">
                        <TableCell
                          colSpan={6}
                          className="py-6 text-center text-xs text-muted-foreground"
                          data-testid="global-leaderboard-empty"
                        >
                          Leaderboard data is temporarily unavailable.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="mt-12">
          <Card className="border-[hsl(var(--knd-amber))]/20 bg-[hsl(var(--knd-amber))]/5">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div className="min-w-0 flex-1">
                <CardTitle className="text-lg text-[hsl(var(--knd-amber))] truncate">Tournament Prep</CardTitle>
                <p className="text-[10px] sm:text-sm text-muted-foreground truncate">Estimate attendee likelihood and expected meta share for your next event</p>
              </div>
              <Button asChild variant="outline" size="sm" className="border-[hsl(var(--knd-amber))]/40 bg-card/60">
                <Link href="/tournament-likelihood">Run Simulator</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-3 sm:px-6">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3 sm:gap-4">
                <div className="rounded-lg border border-border/60 bg-card/40 p-3 sm:p-4">
                  <h4 className="text-xs font-semibold text-foreground mb-1">Meta Simulation</h4>
                  <p className="text-[10px] text-muted-foreground">Simulate field compositions based on recent patterns.</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-card/40 p-3 sm:p-4">
                  <h4 className="text-xs font-semibold text-foreground mb-1">Archetype Coverage</h4>
                  <p className="text-[10px] text-muted-foreground">Identify deck types likely to appear in your region.</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-card/40 p-3 sm:p-4">
                  <h4 className="text-xs font-semibold text-foreground mb-1">Conversion Odds</h4>
                  <p className="text-[10px] text-muted-foreground">Calculate probability of reaching the top cut.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

      </main>
    </div>
  );
}

function DateBlock({ date }: { date: string }) {
  const d = new Date(`${date}T00:00:00`);
  const month = d.toLocaleString("en-US", { month: "short" }).toUpperCase();

  return (
    <span className="flex w-11 shrink-0 flex-col items-center border-r border-border/70 pr-3">
      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{month}</span>
      <span className="font-mono text-xl font-semibold leading-none text-foreground">{d.getDate()}</span>
    </span>
  );
}

