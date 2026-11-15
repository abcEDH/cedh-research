import Link from "next/link";
import { normalizeDisplayString } from "@/lib/utils";
import { ColorBadge } from "@/components/commanders/stat-card";
import { CommanderArt } from "@/components/commanders/commander-art";
import { CommanderHeaderBackdrop } from "@/components/commanders/commander-header-backdrop";
import type { ScryfallArtByName } from "@/lib/commanders/fetchers";

export function CommanderDetailHeader({
  commanderName,
  archetype,
  colorIdentity,
  commanderArt,
}: {
  commanderName: string;
  archetype: string | null;
  colorIdentity: (string | null | undefined)[] | null | undefined;
  commanderArt: ScryfallArtByName;
}) {
  return (
    <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
      <CommanderHeaderBackdrop name={commanderName} />
      <div className="knd-watermark absolute inset-0" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_80%_at_80%_0%,hsl(var(--knd-magenta)/0.18),transparent_60%)]" />
      <div className="relative">
        <Link href="/commanders" className="text-sm text-muted-foreground hover:text-foreground">
          ← Back to Commanders
        </Link>
        <div className="mt-5 grid gap-6 lg:grid-cols-[auto_1fr] lg:items-center">
          <CommanderArt name={commanderName} size={112} artByName={commanderArt} />
          <div>
            <div className="flex items-center gap-3">
              {colorIdentity?.filter(Boolean).map((color) => (
                <ColorBadge key={color} color={color as string} size="lg" />
              ))}
            </div>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              {normalizeDisplayString(commanderName)}
            </h1>
            {archetype && (
              <p className="text-muted-foreground mt-1">{normalizeDisplayString(archetype)}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
