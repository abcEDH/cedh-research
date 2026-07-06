import Link from "next/link";
import type { GameConfig } from "@/lib/games/registry";

const NAV_ITEMS = [
  { href: "/", label: "Meta" },
  { href: "/tournaments", label: "Tournaments" },
];

export function SiteHeader({ game }: { game: GameConfig }) {
  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/80 backdrop-blur-xl">
      <div className="container mx-auto flex flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
        <Link
          href="/"
          aria-label={game.name}
          className="text-xl font-semibold text-foreground transition hover:text-primary"
        >
          {game.name}
          <span className="ml-2 text-sm font-normal text-muted-foreground">Meta</span>
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-[10px] px-3.5 py-2 transition hover:bg-muted/40 hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
          {game.externalLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              target="_blank"
              rel="noreferrer"
              className="rounded-[10px] px-3.5 py-2 transition hover:bg-muted/40 hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
