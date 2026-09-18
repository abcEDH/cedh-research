import { normalizeDisplayString } from "@/lib/utils";
import type { RecentFinish } from "@/lib/commanders/fetchers";

export function RecentFinishRow({ finish }: { finish: RecentFinish }) {
  const deckHost = (() => {
    if (!finish.decklist_url) return null;
    const url = finish.decklist_url.toLowerCase();
    if (url.includes("moxfield.com")) return "Moxfield";
    if (url.includes("topdeck.gg")) return "TopDeck";
    if (url.includes("archidekt.com")) return "Archidekt";
    return "Decklist";
  })();

  const tournamentUrl = finish.tournament.topdeck_tid
    ? `https://topdeck.gg/event/${finish.tournament.topdeck_tid}`
    : null;
  const playerDisplay = finish.player_name || finish.player_handle;
  const playerProfileUrl = finish.player_id
    ? `https://topdeck.gg/profile/${finish.player_id}`
    : null;
  const topdeckDeckUrl =
    finish.tournament.topdeck_tid && (finish.player_id || finish.player_handle)
      ? `https://topdeck.gg/deck/${finish.tournament.topdeck_tid}/${finish.player_id || finish.player_handle}`
      : null;
  const decklistHref = finish.decklist_url || topdeckDeckUrl;

  const dateLabel = new Date(finish.tournament.start_date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  let medalLabel = finish.tournament.player_count <= 34 ? "Top 4" : "Top 16";
  let medalClass = "border-[hsl(var(--knd-amber))]/40 text-[hsl(var(--knd-amber))]";
  if (finish.final_standing === 1) {
    medalLabel = "1st";
    medalClass = "border-[hsl(var(--knd-amber))]/60 text-[hsl(var(--knd-amber))]";
  } else if (finish.made_top_cut) {
    medalLabel = "Top Cut";
    medalClass = "border-primary/40 text-primary";
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full border px-2 py-0.5 text-xs ${medalClass}`}>
            {medalLabel}
          </span>
          {tournamentUrl ? (
            <a
              href={tournamentUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-foreground truncate hover:text-primary"
            >
              {normalizeDisplayString(finish.tournament.name)}
            </a>
          ) : (
            <p className="text-sm font-medium text-foreground truncate">
              {normalizeDisplayString(finish.tournament.name)}
            </p>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {dateLabel} · {finish.tournament.player_count} players
          {finish.final_standing ? ` · Standing ${finish.final_standing}` : ""}
        </p>
        {playerDisplay ? (
          <p className="text-xs text-muted-foreground mt-1">
            Player{" "}
            {playerProfileUrl ? (
              <a
                href={playerProfileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground hover:text-primary"
              >
                {playerDisplay}
              </a>
            ) : (
              <span className="text-foreground">{playerDisplay}</span>
            )}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {decklistHref ? (
          <a
            href={decklistHref}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-border/60 px-3 py-1 text-muted-foreground hover:border-primary/40 hover:text-foreground"
          >
            {deckHost || (topdeckDeckUrl ? "TopDeck" : "Decklist")}
          </a>
        ) : null}
      </div>
    </div>
  );
}
