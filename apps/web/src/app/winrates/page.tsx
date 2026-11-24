import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DateRangeFilter from "@/components/winrates/date-range-filter";
import MatchupMatrixTable from "@/components/winrates/matchup-matrix-table";
import { getWinrateMatrixData } from "@/lib/winrates/fetchers";
import { parseDaysBack } from "@/lib/winrates/stats";

export const revalidate = 3600;

export default async function WinratesPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedParams = await searchParams;
  const daysBack = parseDaysBack(resolvedParams.days);
  const { commanderOrder, rows, evByCommander } = await getWinrateMatrixData(daysBack);

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-semibold text-foreground md:text-4xl">Winrate Matrix</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Top {commanderOrder.length || 30} commanders by metashare, pairwise matchups with 95%
            confidence intervals. Each cell stacks the CI, point winrate, and sample size --
            mirroring mtgdecks.net&apos;s visual grammar.
          </p>
        </div>

        <Card>
          <CardHeader className="knd-panel-header flex-row flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-lg">Matchup Matrix</CardTitle>
            <DateRangeFilter />
          </CardHeader>
          <CardContent>
            <MatchupMatrixTable
              commanderOrder={commanderOrder}
              rows={rows}
              evRows={Array.from(evByCommander.values())}
            />
            <p className="mt-3 text-xs text-muted-foreground">
              OVERALL is each deck&apos;s aggregate winrate across every opponent in the window.
              EV is the meta-share-weighted expected pod winrate (see the commander page&apos;s
              META EV badge for the plain-English definition). Mirror cells (a commander against
              itself) always read 50% at the deck&apos;s full sample size.
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
