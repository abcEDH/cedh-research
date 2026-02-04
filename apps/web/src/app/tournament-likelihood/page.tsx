import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function TournamentLikelihoodPage() {
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="knd-chip">Tournament Prep</p>
              <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
                Pre-Tournament Meta Scouting
              </h1>
            </div>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <Link className="transition hover:text-foreground" href="/">
                Home
              </Link>
              <Link className="transition hover:text-foreground" href="/regional-elo">
                Regional Elo
              </Link>
              <Link className="transition hover:text-foreground" href="/midseason-invitational">
                MidSeason
              </Link>
            </nav>
          </div>
          <p className="max-w-4xl text-base text-muted-foreground">
            This workflow is temporarily paused while we stabilize data freshness and UX.
          </p>
        </header>

        <Card className="knd-panel mt-8">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">On Ice</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Tournament scouting is temporarily disabled. We will re-enable it after we ship a loading
              state, clearer progress, and more reliable attendee/deck inference.
            </p>
            <div className="mt-4">
              <Link className="text-sm text-primary underline underline-offset-4" href="/midseason-invitational">
                Use MidSeason Invitational prep instead
              </Link>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
