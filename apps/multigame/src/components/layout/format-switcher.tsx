import Link from "next/link";
import type { GameFormat } from "@/lib/games/registry";
import { cn } from "@/lib/utils";

export function FormatSwitcher({
  formats,
  activeFormat,
  basePath = "/",
}: {
  formats: GameFormat[];
  activeFormat: string;
  basePath?: string;
}) {
  return (
    <nav aria-label="Format" className="flex flex-wrap items-center gap-1">
      {formats.map((format) => (
        <Link
          key={format.slug}
          href={`${basePath}?format=${format.slug}`}
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
