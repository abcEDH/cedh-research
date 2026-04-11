import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata = {
  title: "Data Model | cEDH Analytics",
  description: "Supabase schema and curated views powering cEDH Analytics.",
};

const sections = [
  {
    title: "Core Tables",
    body: [
      "tournaments: TopDeck.gg events (location, dates, player_count, rounds, top_cut).",
      "players: TopDeck.gg player identities (name, topdeck_id).",
      "commanders: Commander or partner combinations (name, color_identity, scryfall_ids).",
      "tournament_entries: One player’s entry in one tournament (results, standings, decklist).",
      "games: Individual pod games within a tournament round.",
      "game_participants: One player’s seat and result in a game.",
      "commander_matchups: Commander-vs-commander outcomes per game.",
    ],
  },
  {
    title: "Curated Views",
    body: [
      "commander_stats: Aggregate entries, win rate, and top cut conversion.",
      "commander_weekly_trends / commander_monthly_trends / commander_wow_mom: Trend rollups.",
      "card_frequencies_by_commander / card_frequencies_global: Inclusion rates.",
      "card_performance_by_commander / card_performance_global: Card performance.",
      "player_tournament_journey / pod_composition / player_seat_distribution: Round-level journeys.",
      "global_elo_* views: Global Elo ratings and leaderboards.",
      "player_commander_entries: Fast per-player commander history for meta prep.",
    ],
  },
  {
    title: "Conventions",
    body: [
      "Most analytics filter to tournaments with player_count >= 32.",
      "Partner commanders are stored as one combined identity.",
      "Unknown Commander rows are excluded from most analytics and prep outputs.",
    ],
  },
  {
    title: "Source of Truth",
    body: [
      "Primary schema definitions live in Supabase migrations under packages/backend/supabase/migrations.",
      "Summarized dictionary lives in packages/backend/docs/data_dictionary.md.",
    ],
  },
];

export default function DataModelPage() {
  return (
    <div className="min-h-screen">
      <main className="container mx-auto max-w-4xl px-4 py-8">
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <div className="knd-watermark absolute inset-0" />
          <div className="relative">
            <Link href="/about" className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to About
            </Link>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              Data Model
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Supabase schema and curated views that power the analytics UI.
            </p>
          </div>
        </div>

        {sections.map((section) => (
          <Card key={section.title} className="mb-6 border-border/60 bg-card/60">
            <CardHeader>
              <CardTitle className="text-primary">{section.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              {section.body.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </CardContent>
          </Card>
        ))}

        <Card className="border-border/60 bg-card/60">
          <CardHeader>
            <CardTitle className="text-[hsl(var(--knd-amber))]">Reference</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Detailed ERD and field descriptions live at{" "}
              <code>packages/backend/docs/data_dictionary.md</code>.
            </p>
            <p>
              Local documentation mirror: <code>docs/methodology/data-model.md</code>.
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
