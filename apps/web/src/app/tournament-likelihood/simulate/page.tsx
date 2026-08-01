import { Card, CardContent } from "@/components/ui/card";
import { extractTournamentSlug, fetchTournamentBySlug } from "@/lib/topdeck";
import Link from "next/link";
import { SimulationRunner } from "./simulation-runner";

export const dynamic = "force-dynamic";

type SearchParams =
  | Record<string, string | string[] | undefined>
  | URLSearchParams
  | undefined;

function readStringParam(params: SearchParams, key: string) {
  if (!params) return "";
  if (typeof (params as URLSearchParams).get === "function") {
    return (params as URLSearchParams).get(key) ?? "";
  }
  const value = (params as Record<string, string | string[] | undefined>)[key];
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function readPositiveIntegerParam(params: SearchParams, key: string) {
  const value = readStringParam(params, key).trim();
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function readNonNegativeIntegerParam(params: SearchParams, key: string) {
  const value = readStringParam(params, key).trim();
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

export default async function TournamentSimulationPage({
  searchParams,
}: {
  searchParams?:
    | Promise<{
        tournament?: string;
        swissRounds?: string;
        topCut?: string;
        runSeconds?: string;
        dropAfterRound?: string;
        dropMinPoints?: string;
      }>
    | {
        tournament?: string;
        swissRounds?: string;
        topCut?: string;
        runSeconds?: string;
        dropAfterRound?: string;
        dropMinPoints?: string;
      };
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const tournamentInput = readStringParam(resolvedSearchParams, "tournament").trim();
  const slug = extractTournamentSlug(tournamentInput);
  const requestedSwissRounds = readPositiveIntegerParam(resolvedSearchParams, "swissRounds");
  const requestedTopCut = readNonNegativeIntegerParam(resolvedSearchParams, "topCut");
  const requestedRunSeconds = readPositiveIntegerParam(resolvedSearchParams, "runSeconds");
  const requestedDropAfterRound = readPositiveIntegerParam(resolvedSearchParams, "dropAfterRound");
  const requestedDropMinPoints = readNonNegativeIntegerParam(resolvedSearchParams, "dropMinPoints");

  let tournamentName = slug || "Simulate Tournament";
  let playerCount = 0;
  const defaultSwissRounds = 6;
  const defaultTopCut = 40;
  const defaultRunSeconds = 600;
  let settingsError: string | null = null;

  if (slug) {
    try {
      const tournament = await fetchTournamentBySlug(slug);
      tournamentName = tournament.data.name || slug;
      playerCount = tournament.standings.length;
    } catch (error) {
      settingsError = (error as Error).message;
    }
  }

  const swissRounds = requestedSwissRounds ?? defaultSwissRounds;
  const topCut = requestedTopCut ?? defaultTopCut;
  const runSeconds = requestedRunSeconds ?? defaultRunSeconds;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="knd-chip">Tournament Simulation</p>
              <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
                {tournamentName}
              </h1>
            </div>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <Link className="transition hover:text-foreground" href="/tournament-likelihood">
                Tournament Prep
              </Link>
              <Link className="transition hover:text-foreground" href="/">
                Home
              </Link>
            </nav>
          </div>
        </header>

        {!slug && (
          <Card className="knd-panel mt-8">
            <CardContent className="text-sm text-muted-foreground">
              Open this page from Tournament Prep or add a TopDeck tournament slug.
            </CardContent>
          </Card>
        )}

        {settingsError && (
          <div className="mt-6 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            Failed to load tournament settings: {settingsError}
          </div>
        )}

        {slug && !settingsError && (
          <SimulationRunner
            defaultSwissRounds={swissRounds}
            defaultTopCut={topCut}
            defaultRunSeconds={runSeconds}
            defaultDropAfterRound={requestedDropAfterRound}
            defaultDropMinPoints={requestedDropMinPoints}
            playerCount={playerCount}
            slug={slug}
          />
        )}
      </main>
    </div>
  );
}
