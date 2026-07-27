import Link from "next/link";
import type { ReactNode } from "react";

export function EloGameFilter({
  eloOnly,
  allGamesHref,
  rankingGamesHref,
}: {
  eloOnly: boolean;
  allGamesHref: string;
  rankingGamesHref: string;
}) {
  const toggleHref = eloOnly ? allGamesHref : rankingGamesHref;

  return (
    <CardLike>
      <div>
        <div className="text-sm font-medium text-foreground">Game filter</div>
        <p className="text-xs text-muted-foreground">
          Aggregate W-L-D stats default to Elo-worthy events with 30+ players; Elo rankings are unchanged.
        </p>
      </div>
      <div className="flex min-h-11 items-center gap-3">
        <span className="text-sm text-foreground">Show 30+ player games only</span>
        <Link
          href={toggleHref}
          role="switch"
          aria-checked={eloOnly}
          aria-label="Show 30+ player games only"
          className="inline-flex min-h-11 min-w-11 items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        >
          <span
            aria-hidden="true"
            className={`relative block h-6 w-11 rounded-full transition-colors ${
              eloOnly ? "bg-primary" : "bg-muted-foreground/40"
            }`}
          >
            <span
              className={`absolute top-1 h-4 w-4 rounded-full bg-background shadow-sm transition-transform ${
                eloOnly ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </span>
        </Link>
      </div>
    </CardLike>
  );
}

function CardLike({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-card px-4 py-4">
      {children}
    </div>
  );
}
