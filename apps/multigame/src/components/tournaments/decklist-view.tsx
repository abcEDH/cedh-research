import Image from "next/image";
import { DecklistObjSchema } from "@/lib/schemas/api-contracts";
import type { CardImageProvider } from "@/lib/games/card-images";

const SECTION_ORDER = ["Commanders", "Mainboard", "Sideboard"];

export function DecklistView({
  decklistObj,
  provider,
}: {
  decklistObj: unknown;
  provider: CardImageProvider;
}) {
  const parsed = DecklistObjSchema.safeParse(decklistObj);
  if (!parsed.success) {
    return <p className="text-sm text-muted-foreground">No decklist available.</p>;
  }

  const sections = Object.entries(parsed.data).sort(
    ([a], [b]) => sectionRank(a) - sectionRank(b)
  );
  if (sections.length === 0) {
    return <p className="text-sm text-muted-foreground">No decklist available.</p>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {sections.map(([sectionName, cards]) => (
        <section key={sectionName}>
          <h4 className="mb-2 text-sm font-semibold text-foreground">{sectionName}</h4>
          <ul className="space-y-1 text-sm text-muted-foreground">
            {Object.entries(cards).map(([cardName, card]) => {
              const imageUrl = provider.imageUrl({ name: cardName, externalId: card.id });
              const externalUrl = provider.externalUrl({ name: cardName });
              return (
                <li key={cardName} className="flex items-center gap-2">
                  {imageUrl ? (
                    <Image
                      src={imageUrl}
                      alt={cardName}
                      width={24}
                      height={35}
                      className="h-[35px] w-6 rounded-sm object-cover"
                      unoptimized
                    />
                  ) : null}
                  <span className="tabular-nums">{card.count}×</span>
                  {externalUrl ? (
                    <a
                      href={externalUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="transition hover:text-primary"
                    >
                      {cardName}
                    </a>
                  ) : (
                    <span>{cardName}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

function sectionRank(name: string): number {
  const index = SECTION_ORDER.indexOf(name);
  return index === -1 ? SECTION_ORDER.length : index;
}
