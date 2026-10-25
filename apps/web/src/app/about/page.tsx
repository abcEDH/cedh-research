import Link from "next/link";
import { ArrowUpRight, ChartNoAxesCombined, Compass, Layers, Trophy, Users } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export const metadata = {
  title: "About | tedh.gg",
  description:
    "Explore cEDH tournament results, scout the field, and understand the data and forecasts behind tedh.gg.",
};

const tools = [
  {
    title: "Scout your next tournament",
    href: "/tournament-likelihood",
    icon: Compass,
    description: "Paste a TopDeck event link to explore its attendees, their recent commander choices, and a forecast of the field you may face.",
  },
  {
    title: "Explore tournament results",
    href: "/tournaments",
    icon: Trophy,
    description: "Browse events and inspect their standings, players, and recorded games. Follow the results back to the tournament that produced them.",
  },
  {
    title: "Find players and review performance",
    href: "/regional-elo",
    icon: Users,
    description: "Explore global and regional leaderboards, then open a player profile for event history, commander choices, and opponent matchups.",
  },
  {
    title: "Compare commanders",
    href: "/commanders",
    icon: Layers,
    description: "Compare entries, win rates, and conversion rates. Commander profiles bring together results, matchups, notable players, and card choices.",
  },
  {
    title: "Follow the metagame",
    href: "/commanders/trends",
    icon: ChartNoAxesCombined,
    description: "Track changes in commander representation and results over time to put a recent breakout or a familiar favorite in context.",
  },
  {
    title: "Investigate card choices",
    href: "/trap-spice",
    icon: Compass,
    description: "Use Trap & Spice to find popular cards associated with weaker results and less common cards associated with stronger results. Treat these as leads for testing.",
  },
];

const metrics = [
  ["Win rate", "The share of recorded games won. Draws remain part of the game count; entries count tournament appearances, not games."],
  ["Conversion rates", "The share of entries reaching the indicated finish or cut. Top 16 / Top 10 / Top 4 is a size-adjusted finish measure; Top Cut Conversion tracks the event’s cut. Check the label when comparing events."],
  ["Points per game", "A comparison metric using 5 points for a win, 1 for a draw, and 0 for a loss. This is separate from an event’s own standings and tiebreakers."],
  ["Resiliency", "The share of games ending in a win or draw. Read it alongside win rate: avoiding a loss and winning a game describe different outcomes."],
];

const actionClass = "inline-flex min-h-11 items-center gap-2 rounded-md border border-border/60 px-4 py-2 text-sm text-foreground transition-colors hover:border-primary/60 hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary";

export default function AboutPage() {
  return (
    <main className="container mx-auto max-w-5xl space-y-10 px-4 py-8 md:py-12">
      <header className="relative overflow-hidden rounded-2xl border border-border/70 bg-card/60 p-6 md:p-10">
        <div className="knd-watermark pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="relative max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-primary">About tedh.gg</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground md:text-5xl">
            Know the field. Prepare with context.
          </h1>
          <p className="mt-5 text-base leading-relaxed text-muted-foreground md:text-lg">
            tedh.gg turns competitive Commander tournament data into tools for preparation
            and performance review. Explore what people play, how they perform, and what
            you might face at your next event.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/tournament-likelihood" className={actionClass}>Scout a tournament <ArrowUpRight size={16} aria-hidden="true" /></Link>
            <Link href="/commanders" className={actionClass}>Explore commanders</Link>
          </div>
        </div>
      </header>

      <section aria-labelledby="tools-heading">
        <h2 id="tools-heading" className="text-2xl font-semibold">Make the data useful</h2>
        <p className="mt-2 text-muted-foreground">Start with the question you want to answer.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {tools.map(({ title, href, icon: Icon, description }) => (
            <Link key={href} href={href} className="group rounded-xl border border-border/60 bg-card/60 p-5 transition-colors hover:border-primary/50 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary">
              <Icon size={22} className="mb-4 text-primary" aria-hidden="true" />
              <h3 className="flex items-start justify-between gap-3 font-semibold text-foreground">
                {title}<ArrowUpRight size={18} className="shrink-0 text-muted-foreground group-hover:text-primary" aria-hidden="true" />
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="ratings-heading">
        <h2 id="ratings-heading" className="text-2xl font-semibold">Ratings and forecasts measure different things</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Card className="border-border/60 bg-card/60">
            <CardHeader><h3 className="font-semibold text-primary">Player ratings</h3></CardHeader>
            <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
              <p>Leaderboards and ranking tables display TopDeck Elo. Regional rankings help you explore players by their recorded activity; they do not represent a separate regional skill rating.</p>
              <p>Predictions and simulations use a separate internal Elo model. It accounts for seating and distinguishes Swiss, top cut, draws, and league games. Its ratings are model inputs, not the Elo shown on the leaderboard.</p>
            </CardContent>
          </Card>
          <Card className="border-border/60 bg-card/60">
            <CardHeader><h3 className="font-semibold text-primary">Commander forecasts</h3></CardHeader>
            <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
              <p>Player commander forecasts use recorded deck history, weighting recent choices and the latest commander played. Tournament prep combines those estimates into an expected field.</p>
              <p>A 40% modeled commander share estimates a player’s deck choice. It is not a 40% chance to win, or confirmation that the deck is registered. Players can switch decks, and missing history reduces coverage.</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section aria-labelledby="data-heading" className="rounded-xl border border-border/60 bg-card/60 p-6">
        <h2 id="data-heading" className="text-2xl font-semibold">Where the data comes from</h2>
        <div className="mt-4 space-y-3 text-sm leading-relaxed text-muted-foreground">
          <p>Tournament results, standings, and linked decklists come from <a href="https://topdeck.gg" className="text-primary underline underline-offset-4">TopDeck.gg</a>. Our dataset includes tournaments of different sizes and leagues. Coverage depends on what is published, available, and successfully imported.</p>
          <p>We normalize player, commander, and location records to make results easier to compare. Partner commanders are treated as a combined commander identity. Pages apply their own date windows, filters, and eligibility rules, so totals can differ between views.</p>
          <p>Recorded results and modeled outputs are separate. Tournament prep can use an upcoming event’s attendee list; historical performance depends on available results. Imports, rating updates, and cached pages refresh separately, so a newly reported result may take time to appear everywhere.</p>
        </div>
      </section>

      <section aria-labelledby="metrics-heading">
        <h2 id="metrics-heading" className="text-2xl font-semibold">Read the numbers in context</h2>
        <dl className="mt-5 grid gap-5 sm:grid-cols-2">
          {metrics.map(([term, definition]) => (
            <div key={term} className="border-l-2 border-primary/40 pl-4">
              <dt className="font-semibold text-foreground">{term}</dt>
              <dd className="mt-2 text-sm leading-relaxed text-muted-foreground">{definition}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-6 rounded-xl border border-border/60 bg-muted/20 p-5 text-sm leading-relaxed text-muted-foreground">
          <h3 className="mb-2 font-semibold text-foreground">Evidence, with limits</h3>
          <p>Small samples can swing sharply. More games help, but no game-count threshold alone guarantees statistical confidence. Player skill, seating, event strength, draws, and changes in the metagame all affect comparisons.</p>
          <p className="mt-3">A 25% win rate is an equal-share reference for four players when every game has a winner. Draws lower that baseline. A card or commander appearing in winning decks does not establish that it caused those wins.</p>
          <p className="mt-3">Opponent matchup records come from multiplayer pods, not isolated one-on-one matches. Use them to explore history, not as a guaranteed prediction of the next game.</p>
        </div>
      </section>

      <section aria-labelledby="feedback-heading" className="rounded-xl border border-border/60 bg-card/60 p-6">
        <h2 id="feedback-heading" className="text-2xl font-semibold">Help improve the picture</h2>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">Found a missing result, duplicate player, or incorrect commander? Include the tournament or player link and what looks wrong so we can investigate. Feature ideas and contributions are welcome too.</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <a href="mailto:contact@tedh.gg" className={actionClass}>Report an issue</a>
          <a href="https://discord.gg/MZCkEakB3d" className={actionClass}>Join the Discord</a>
          <a href="https://github.com/abcEDH/cedh-research" className={actionClass}>Explore the project</a>
        </div>
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-1 border-t border-border/60 pt-4">
          <Link href="/limitations" className="inline-flex min-h-11 items-center text-sm text-primary hover:underline">Data limitations</Link>
          <Link href="/methodology/data-model" className="inline-flex min-h-11 items-center text-sm text-primary hover:underline">Data methodology</Link>
        </div>
      </section>
    </main>
  );
}
