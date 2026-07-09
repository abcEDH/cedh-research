import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getGame } from "@/lib/games/registry";
import { getCardImageProvider } from "@/lib/games/card-images";
import { withGameParam } from "@/lib/games/links";
import { fetchTournamentDetail } from "@/lib/tournaments/fetchers";
import { formatDate } from "@/lib/tournaments/stats";
import { isSupabaseConfigured } from "@/lib/supabase";
import { StandingsTable } from "@/components/tournaments/standings-table";

export const revalidate = 86400;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ game: string; tid: string }>;
}): Promise<Metadata> {
  const { tid } = await params;
  const detail = await fetchTournamentDetail(tid);
  return detail ? { title: detail.tournament.name } : { title: "Tournament" };
}

export default async function TournamentDetailPage({
  params,
}: {
  params: Promise<{ game: string; tid: string }>;
}) {
  const { game: slug, tid } = await params;
  const game = getGame(slug);
  if (!game) {
    notFound();
  }

  const detail = await fetchTournamentDetail(tid);
  if (!detail && !isSupabaseConfigured()) {
    return (
      <main className="container mx-auto px-4 py-8">
        <p className="rounded-xl border border-border/70 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
          Supabase is not configured for this deployment. Set NEXT_PUBLIC_SUPABASE_URL and
          NEXT_PUBLIC_SUPABASE_ANON_KEY to load live tournament data.
        </p>
      </main>
    );
  }
  if (!detail || detail.tournament.game !== game.dbGame) {
    notFound();
  }

  const { tournament, entries } = detail;
  const provider = getCardImageProvider(game.cardImages);
  const facts = [
    formatDate(tournament.start_date),
    tournament.format,
    `${tournament.player_count} players`,
    tournament.swiss_rounds !== null ? `${tournament.swiss_rounds} rounds` : null,
    tournament.top_cut !== null ? `Top ${tournament.top_cut}` : null,
  ].filter((fact): fact is string => fact !== null);

  return (
    <main className="container mx-auto flex flex-col gap-6 px-4 py-8">
      <div>
        <Link
          href={withGameParam("/tournaments", game.slug)}
          className="text-sm text-muted-foreground transition hover:text-foreground"
        >
          ← Tournaments
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">{tournament.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{facts.join(" · ")}</p>
      </div>

      <StandingsTable entries={entries} identityNoun={game.identityNoun} provider={provider} />
    </main>
  );
}
