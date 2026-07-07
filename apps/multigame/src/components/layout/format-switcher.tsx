import Link from "next/link";
import type { GameFormat, GameSlug } from "@/lib/games/registry";
import { withGameParam } from "@/lib/games/links";
import { cn } from "@/lib/utils";

export function FormatSwitcher({
  formats,
  activeFormat,
  gameSlug,
  basePath = "/",
}: {
  formats: GameFormat[];
  activeFormat: string;
  gameSlug: GameSlug;
  basePath?: string;
}) {
  return (
    <nav aria-label="Format" className="flex flex-wrap items-center gap-1">
      {formats.map((format) => (
        <Link
          key={format.slug}
          href={withGameParam(basePath, gameSlug, { format: format.slug })}
          className={cn(
            "rounded-full border px-3 py-1 text-sm transition",
            format.slug === activeFormat
              ? "border-primary/60 bg-primary/10 font-semibold text-foreground"
              : "border-border/70 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
          )}
        >
          {format.name}
        </Link>
      ))}
    </nav>
  );
}
