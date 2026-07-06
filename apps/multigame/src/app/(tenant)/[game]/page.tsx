import { notFound } from "next/navigation";
import { getGame, resolveFormat } from "@/lib/games/registry";
import { fetchDeckIdentityStats } from "@/lib/archetypes/fetchers";
import { totalEntries } from "@/lib/archetypes/stats";
import { isSupabaseConfigured } from "@/lib/supabase";
import { ArchetypeStatsTable } from "@/components/archetypes/archetype-stats-table";
import { FormatSwitcher } from "@/components/layout/format-switcher";

export const revalidate = 900;

export default async function MetaOverviewPage({
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
  const rows = await fetchDeckIdentityStats({ game: game.dbGame, format: format.dbFormat });
  const entries = totalEntries(rows);

  return (
    <main className="container mx-auto flex flex-col gap-6 px-4 py-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            {game.name} meta
            {format.dbFormat !== null ? (
              <span className="ml-2 text-lg font-normal text-muted-foreground">{format.name}</span>
            ) : null}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {rows.length > 0
              ? `${rows.length} ${game.identityNoun.toLowerCase()}s across ${entries} tournament entries.`
              : game.tagline}
          </p>
        </div>
        {game.formats.length > 1 ? (
          <FormatSwitcher formats={game.formats} activeFormat={format.slug} basePath="/" />
        ) : null}
      </div>

      {!isSupabaseConfigured() && rows.length === 0 ? (
        <p className="rounded-xl border border-border/70 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
          Supabase is not configured for this deployment. Set NEXT_PUBLIC_SUPABASE_URL and
          NEXT_PUBLIC_SUPABASE_ANON_KEY to load live tournament data.
        </p>
      ) : (
        <ArchetypeStatsTable rows={rows} identityNoun={game.identityNoun} />
      )}
    </main>
  );
}
