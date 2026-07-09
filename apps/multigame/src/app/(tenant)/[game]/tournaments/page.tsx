import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getGame, resolveFormat } from "@/lib/games/registry";
import { fetchTournaments } from "@/lib/tournaments/fetchers";
import { isSupabaseConfigured } from "@/lib/supabase";
import { TournamentsList } from "@/components/tournaments/tournaments-list";
import { FormatSwitcher } from "@/components/layout/format-switcher";

export const revalidate = 900;

export const metadata: Metadata = {
  title: "Tournaments",
};

export default async function TournamentsPage({
  params,
  searchParams,
}: {
  params: Promise<{ game: string }>;
  searchParams: Promise<{ format?: string }>;
}) {
  const { game: slug } = await params;
  const game = getGame(slug);
  if (!game) {
    notFound();
  }

  const { format: formatSlug } = await searchParams;
  const format = resolveFormat(game, formatSlug);
  const tournaments = await fetchTournaments({ game: game.dbGame, format: format.dbFormat });

  return (
    <main className="container mx-auto flex flex-col gap-6 px-4 py-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Tournaments</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {game.name} events ingested from TopDeck.gg, newest first.
          </p>
        </div>
        {game.formats.length > 1 ? (
          <FormatSwitcher
            formats={game.formats}
            activeFormat={format.slug}
            gameSlug={game.slug}
            basePath="/tournaments"
          />
        ) : null}
      </div>

      {!isSupabaseConfigured() && tournaments.length === 0 ? (
        <p className="rounded-xl border border-border/70 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
          Supabase is not configured for this deployment. Set NEXT_PUBLIC_SUPABASE_URL and
          NEXT_PUBLIC_SUPABASE_ANON_KEY to load live tournament data.
        </p>
      ) : (
        <TournamentsList tournaments={tournaments} gameSlug={game.slug} />
      )}
    </main>
  );
}
