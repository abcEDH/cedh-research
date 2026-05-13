import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export const metadata = {
  title: "About | tedh.gg",
  description:
    "Methodology, statistics, and technical details behind tedh.gg",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <div className="knd-watermark absolute inset-0" />
          <div className="relative">
            <Link
              href="/"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to Home
            </Link>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              About tedh.gg
            </h1>
            <p className="text-muted-foreground mt-2">
              Methodology, statistics, and technical details.
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              See <Link href="/limitations" className="text-foreground hover:text-primary">data limitations</Link> for known caveats.
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Elo details:{" "}
              <Link href="/methodology/elo" className="text-foreground hover:text-primary">
                cEDH Skill Rating methodology
              </Link>
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Data model:{" "}
              <Link href="/methodology/data-model" className="text-foreground hover:text-primary">
                Supabase schema + curated views
              </Link>
            </p>
          </div>
        </div>

        {/* Data Inclusion */}
        <Card className="bg-card/60 border-border/60 mb-8">
          <CardHeader>
            <CardTitle className="text-[hsl(var(--knd-amber))]">Data Inclusion</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground space-y-4">
            <div className="p-4 bg-muted/30 rounded-lg border border-[hsl(var(--knd-amber))]/30">
              <p className="text-foreground font-medium mb-2">
                All findings are based on games played on the Topdeck platform.
              </p>
            </div>
            <ul className="list-disc list-inside space-y-2 text-sm">
              <li>Tournament and League data sourced from TopDeck.gg API</li>
              <li>Only completed tournaments/leagues with published standings are included</li>
              <li>Decklist data parsed and normalized for card frequency analysis</li>
              <li>Partner commanders are tracked as a single combined commander identity</li>
            </ul>
          </CardContent>
        </Card>

        {/* Primary Statistics */}
        <Card className="bg-card/60 border-border/60 mb-8">
          <CardHeader>
            <CardTitle className="text-primary">Primary Statistics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <StatisticSection
              title="Win Rate"
              formula="Win Rate = Wins / Total Games"
              description="The percentage of games won by a commander. In a 4-player pod, the expected (baseline) win rate is 25% - anything above this indicates above-average performance."
              example="A commander with 150 wins in 500 games has a 30% win rate (150/500 = 0.30), which is 5 percentage points above expected."
            />

            <StatisticSection
              title="Conversion Rate (Top 16 / Top 10 / Top 4)"
              formula="Conversion Rate = Top Bracket Finishes / Total Entries"
              description="The percentage of tournament entries that result in a top-bracket finish. Under 64 players, some events use a Top 10 cutoff, and for 34 players or fewer we only count Top 4 finishes."
              example="A commander with 25 top-bracket finishes from 100 entries has a 25% conversion rate."
            />

            <StatisticSection
              title="Top Cut Conversion"
              formula="Top Cut Conversion = Top Cut Finishes / Total Entries"
              description="The percentage of tournament entries that make the event's top cut bracket."
              example="A commander with 12 top cuts from 80 entries has a 15% top cut conversion rate."
            />

            <StatisticSection
              title="Points per Game"
              formula="Points per Game = (Wins * 5 + Draws) / Total Games"
              description="Weighted scoring that values wins at 5 points, draws at 1 point, and losses at 0 points."
              example="A commander with 10 wins, 5 draws, 25 losses across 40 games scores 1.375 points per game."
            />

            <StatisticSection
              title="Resiliency"
              formula="Resiliency = (Wins + Draws) / Total Games"
              description="The share of games that are not losses. Higher resiliency indicates a stronger ability to avoid losing."
              example="A commander with 20 wins and 10 draws across 50 games has 60% resiliency."
            />

            <StatisticSection
              title="Inclusion Rate"
              formula="Inclusion Rate = Decks with Card / Total Decks"
              description="For card analysis, this measures how often a card appears across all decklists for a given commander (or globally). Cards are tiered based on their inclusion rates."
              example="If Sol Ring appears in 95 of 100 decks, its inclusion rate is 95%."
            />

            <div className="p-4 bg-muted/30 rounded-lg">
              <h4 className="text-foreground font-medium mb-2">Card Tiers</h4>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm">
                <div className="text-center p-2 rounded bg-[hsl(var(--knd-cyan))]/15">
                  <span className="text-primary font-semibold">Core</span>
                  <p className="text-muted-foreground">80%+ inclusion</p>
                </div>
                <div className="text-center p-2 rounded bg-[hsl(var(--knd-cyan))]/10">
                  <span className="text-primary font-semibold">Essential</span>
                  <p className="text-muted-foreground">60-79%</p>
                </div>
                <div className="text-center p-2 rounded bg-[hsl(var(--knd-amber))]/15">
                  <span className="text-[hsl(var(--knd-amber))] font-semibold">Common</span>
                  <p className="text-muted-foreground">30-59%</p>
                </div>
                <div className="text-center p-2 rounded bg-muted/40">
                  <span className="text-muted-foreground font-semibold">Flex</span>
                  <p className="text-muted-foreground">10-29%</p>
                </div>
                <div className="text-center p-2 rounded bg-muted/30">
                  <span className="text-muted-foreground font-semibold">Spice</span>
                  <p className="text-muted-foreground">&lt;10%</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Statistical Significance */}
        <Card className="bg-card/60 border-border/60 mb-8">
          <CardHeader>
            <CardTitle className="text-muted-foreground">Statistical Significance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-muted-foreground">
            <p>
              Not all observed differences are meaningful. Statistical significance
              helps us determine whether an observed effect (like a commander&apos;s
              win rate being above 25%) is likely real or just due to random chance.
            </p>

            <StatisticSection
              title="Sample Size Requirements"
              description="We require minimum sample sizes before drawing conclusions. A commander with 5 entries and a 60% win rate is far less reliable than one with 500 entries and a 28% win rate."
            />

            <div className="p-4 bg-muted/30 rounded-lg">
              <h4 className="text-foreground font-medium mb-2">Confidence Levels</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className="text-[hsl(var(--knd-amber))]">★</span>
                  <span className="text-primary font-medium w-20">High</span>
                  <span>100+ games - Strong statistical confidence</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground">★</span>
                  <span className="text-[hsl(var(--knd-amber))] font-medium w-20">Medium</span>
                  <span>30-99 games - Moderate confidence, interpret with caution</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground/50">★</span>
                  <span className="text-[hsl(var(--knd-amber))] font-medium w-20">Low</span>
                  <span>10-29 games - Low confidence, high variance expected</span>
                </div>
              </div>
            </div>

            <StatisticSection
              title="P-Value"
              formula="p < 0.05 indicates statistical significance"
              description="The p-value represents the probability of observing results at least as extreme as the actual results, assuming the null hypothesis is true. In our context, if a commander's win rate appears higher than 25%, the p-value tells us how likely we'd see this by random chance."
            />
          </CardContent>
        </Card>


        {/* Trap and Spice Methodology */}
        <Card className="bg-card/60 border-border/60 mb-8">
          <CardHeader>
            <CardTitle className="text-[hsl(var(--knd-amber))]">Trap &amp; Spice Analysis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-muted-foreground">
            <StatisticSection
              title="Trap Score"
              formula="Trap Score = Inclusion Rate × |Baseline WR - Card WR|"
              description="Identifies popular cards that underperform. Cards with high inclusion rates but below-baseline win rates are 'traps' - widely played despite hurting your chances. The trap score weights by inclusion rate so commonly-played underperformers rank higher."
            />

            <StatisticSection
              title="Spice Identification"
              formula="Spice = Low Inclusion Rate + High Win Rate Delta"
              description="Hidden gems are cards with &lt;10% inclusion but significantly above-baseline win rates. These rarely-played cards may offer competitive advantages that the meta hasn't discovered yet."
            />

            <div className="p-4 bg-muted/30 rounded-lg border border-[hsl(var(--knd-amber))]/30">
              <h4 className="text-foreground font-medium mb-2">Important Caveats</h4>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>
                  <strong>Correlation ≠ Causation:</strong> A card&apos;s correlation
                  with win rate doesn&apos;t mean it causes wins
                </li>
                <li>
                  <strong>Confounding factors:</strong> Better players may play
                  certain cards, skewing results
                </li>
                <li>
                  <strong>Meta context:</strong> A card&apos;s effectiveness depends
                  on the current meta
                </li>
                <li>
                  <strong>Sample size:</strong> Low-inclusion cards have high variance
                  in their statistics
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Technology Stack */}
        <Card className="bg-card/60 border-border/60 mb-8">
          <CardHeader>
            <CardTitle className="text-foreground">Technology Stack</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <TechCard
                title="Frontend"
                items={[
                  { name: "Next.js 16", desc: "React framework with App Router" },
                  { name: "TypeScript", desc: "Type-safe development" },
                  { name: "Tailwind CSS", desc: "Utility-first styling" },
                  { name: "Recharts", desc: "Data visualization" },
                  { name: "Radix UI", desc: "Accessible component primitives" },
                ]}
              />
              <TechCard
                title="Backend"
                items={[
                  { name: "Supabase", desc: "PostgreSQL database + API" },
                  { name: "Materialized Views", desc: "Pre-computed statistics" },
                  { name: "RPC Functions", desc: "Complex queries in PL/pgSQL" },
                  { name: "Edge Functions", desc: "Serverless compute" },
                ]}
              />
              <TechCard
                title="Data Pipeline"
                items={[
                  { name: "TopDeck.gg API", desc: "Tournament data source" },
                  { name: "Python ETL", desc: "Data extraction and loading" },
                  { name: "Scheduled Jobs", desc: "Regular data refreshes" },
                ]}
              />
              <TechCard
                title="Infrastructure"
                items={[
                  { name: "Vercel", desc: "Frontend hosting + CDN" },
                  { name: "Supabase Cloud", desc: "Managed PostgreSQL" },
                  { name: "GitHub Actions", desc: "CI/CD pipeline" },
                ]}
              />
            </div>
          </CardContent>
        </Card>

        {/* Contact / Contributing */}
        <Card className="bg-card/60 border-border/60">
          <CardHeader>
            <CardTitle className="text-foreground">Questions &amp; Feedback</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground">
            <p className="mb-4">
              Have questions about the methodology or found an issue with the data?
              We welcome feedback and contributions.
            </p>
            <div className="flex gap-4">
              <Link
                href="https://github.com"
                className="px-4 py-2 bg-muted/30 border border-border/60 rounded-md hover:border-primary/40 transition-colors"
              >
                View on GitHub
              </Link>
              <Link
                href="https://lnk.bio/tedh_gg"
                className="px-4 py-2 bg-muted/30 border border-border/60 rounded-md hover:border-primary/40 transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                Discord &amp; Contact
              </Link>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function StatisticSection({
  title,
  formula,
  description,
  example,
}: {
  title: string;
  formula?: string;
  description: string;
  example?: string;
}) {
  return (
    <div className="border-l-2 border-border/60 pl-4">
      <h4 className="text-foreground font-medium mb-1">{title}</h4>
      {formula && (
        <code className="block text-sm text-[hsl(var(--knd-amber))] bg-muted/30 px-2 py-1 rounded mb-2 font-mono">
          {formula}
        </code>
      )}
      <p className="text-sm text-muted-foreground">{description}</p>
      {example && (
        <p className="text-sm text-muted-foreground/70 mt-2 italic">Example: {example}</p>
      )}
    </div>
  );
}

function TechCard({
  title,
  items,
}: {
  title: string;
  items: { name: string; desc: string }[];
}) {
  return (
    <div className="p-4 bg-muted/30 rounded-lg">
      <h4 className="text-foreground font-medium mb-3">{title}</h4>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.name} className="text-sm">
            <span className="text-[hsl(var(--knd-amber))] font-medium">{item.name}</span>
            <span className="text-muted-foreground"> - {item.desc}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
