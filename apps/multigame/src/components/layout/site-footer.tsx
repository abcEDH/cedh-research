import type { GameConfig } from "@/lib/games/registry";

export function SiteFooter({ game }: { game: GameConfig }) {
  return (
    <footer className="border-t border-border/60 px-4 py-6 text-center text-xs text-muted-foreground">
      <p>
        Data provided by{" "}
        <a
          href="https://topdeck.gg"
          target="_blank"
          rel="noreferrer"
          className="text-foreground hover:text-primary"
        >
          TopDeck.gg
        </a>
        . Not affiliated with TopDeck.gg.
      </p>
      <p className="mx-auto mt-2 max-w-3xl">{game.compliance.fanContentNotice}</p>
    </footer>
  );
}
