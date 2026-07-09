import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { GAME_SLUGS, getGame } from "@/lib/games/registry";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";

export function generateStaticParams() {
  return GAME_SLUGS.map((game) => ({ game }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ game: string }>;
}): Promise<Metadata> {
  const { game: slug } = await params;
  const game = getGame(slug);
  if (!game) {
    return {};
  }
  return {
    metadataBase: new URL(game.baseUrl),
    title: {
      template: `%s | ${game.name} Meta`,
      default: `${game.name} Meta`,
    },
    description: game.tagline,
  };
}

export default async function TenantLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ game: string }>;
}) {
  const { game: slug } = await params;
  const game = getGame(slug);
  if (!game) {
    notFound();
  }

  return (
    <div data-game={game.slug} className="flex min-h-screen flex-col">
      <SiteHeader game={game} />
      <div className="flex-1">{children}</div>
      <SiteFooter game={game} />
    </div>
  );
}
