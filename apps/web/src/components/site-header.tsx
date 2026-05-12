import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-border/60">
      <div className="container mx-auto flex flex-col gap-4 px-4 py-5 md:flex-row md:items-center md:justify-between">
        <Link href="/" className="text-2xl font-semibold text-foreground transition hover:text-primary">
          tedh.gg
        </Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <Link className="transition hover:text-foreground" href="/regional-elo">
            Leaderboard
          </Link>
          <Link className="transition hover:text-foreground" href="/commanders">
            Commanders
          </Link>
          <Link className="transition hover:text-foreground" href="/tournament-likelihood">
            Tournament Prep
          </Link>
          <Link className="transition hover:text-foreground" href="/about">
            Methodology
          </Link>
        </nav>
      </div>
    </header>
  );
}
