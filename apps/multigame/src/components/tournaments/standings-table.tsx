import type { TournamentEntryRow } from "@/lib/schemas/api-contracts";
import type { CardImageProvider } from "@/lib/games/card-images";
import { formatRecord } from "@/lib/tournaments/stats";
import { formatWinRate } from "@/lib/archetypes/stats";
import { DecklistView } from "@/components/tournaments/decklist-view";

export function StandingsTable({
  entries,
  identityNoun,
  provider,
}: {
  entries: TournamentEntryRow[];
  identityNoun: string;
  provider: CardImageProvider;
}) {
  if (entries.length === 0) {
    return (
      <p className="rounded-xl border border-border/70 bg-card/50 px-6 py-10 text-center text-sm text-muted-foreground">
        No standings available for this tournament.
      </p>
    );
  }

  return (
    <div className="relative w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="[&_tr]:border-b">
          <tr>
            <th className="h-10 px-2 text-left align-middle font-medium whitespace-nowrap">#</th>
            <th className="h-10 px-2 text-left align-middle font-medium whitespace-nowrap">
              {identityNoun}
            </th>
            <th className="h-10 px-2 text-right align-middle font-medium whitespace-nowrap">
              Points
            </th>
            <th className="h-10 px-2 text-right align-middle font-medium whitespace-nowrap">
              W-L-D
            </th>
            <th className="h-10 px-2 text-right align-middle font-medium whitespace-nowrap">
              Win rate
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <StandingsRow
              key={entry.id}
              entry={entry}
              provider={provider}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StandingsRow({
  entry,
  provider,
}: {
  entry: TournamentEntryRow;
  provider: CardImageProvider;
}) {
  const hasDecklist = entry.decklist_obj !== null && entry.decklist_obj !== undefined;

  return (
    <>
      <tr className="border-b transition-colors hover:bg-muted/50">
        <td className="p-2 align-middle tabular-nums">{entry.final_standing ?? "—"}</td>
        <td className="p-2 align-middle font-medium">
          {entry.commanders?.name ?? "Unknown"}
          {hasDecklist ? (
            <details className="mt-1 font-normal">
              <summary className="cursor-pointer text-xs text-muted-foreground transition hover:text-foreground">
                Decklist
              </summary>
              <div className="mt-2">
                <DecklistView decklistObj={entry.decklist_obj} provider={provider} />
              </div>
            </details>
          ) : null}
        </td>
        <td className="p-2 text-right align-middle tabular-nums">{entry.points ?? "—"}</td>
        <td className="p-2 text-right align-middle tabular-nums">
          {formatRecord(entry.wins, entry.losses, entry.draws)}
        </td>
        <td className="p-2 text-right align-middle tabular-nums">
          {formatWinRate(entry.win_rate)}
        </td>
      </tr>
    </>
  );
}
