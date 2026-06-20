import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, Trophy, Users } from "lucide-react";
import { loadTournamentDetail, staticTournamentParams } from "@/lib/tournament-detail-loader";
import { TournamentDetailTabs } from "./tournament-detail-tabs";

type PageProps = {
  params: Promise<{ slug: string }>;
};

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

export function generateStaticParams() {
  return staticTournamentParams();
}

export async function generateMetadata({ params }: PageProps) {
  const { slug } = await params;
  const tournament = await loadTournamentDetail(slug);
  if (!tournament) return {};
  return {
    title: `${tournament.name} | tedh.gg`,
    description: `${tournament.name} standings, commander distribution, and cEDH pod bracket.`,
  };
}

function formatDate(date: string) {
  const d = new Date(`${date}T00:00:00`);
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

export default async function TournamentDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const tournament = await loadTournamentDetail(slug);
  if (!tournament) notFound();

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 pb-20">
      <Link
        href="/tournaments"
        className="mb-7 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Latest Tournaments
      </Link>

      <section className="border-b border-border/70 pb-7">
        <div className="font-mono text-xs uppercase tracking-[0.2em] text-primary">
          {formatDate(tournament.date)} · {tournament.players.toLocaleString()} Players
        </div>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-3xl font-semibold leading-tight tracking-tight md:text-[34px]">
              {tournament.name}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Users className="h-4 w-4 text-primary" />
                {tournament.rounds} Swiss rounds
              </span>
              <span>·</span>
              <span>Top {tournament.cutSize} cut</span>
              <span>·</span>
              <a
                href={tournament.source}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:text-foreground"
              >
                Source
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
          <div className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--knd-amber))]/40 bg-[hsl(var(--knd-amber))]/10 px-3 py-2 text-sm text-[hsl(var(--knd-amber))]">
            <Trophy className="h-4 w-4" />
            {tournament.winner}
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-3 md:grid-cols-4">
        <StatCard label="Players" value={tournament.players.toLocaleString()} />
        <StatCard label="Top Cut" value={String(tournament.cutSize)} sub={`${Math.round((tournament.cutSize / tournament.players) * 100)}%`} />
        <StatCard label="Winner" value={tournament.winner} compact accent />
        <StatCard label="Win Cmd." value={tournament.winnerCmd} compact />
      </section>

      <TournamentDetailTabs tournament={tournament} />
    </main>
  );
}

function StatCard({
  label,
  value,
  sub,
  compact = false,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  compact?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="knd-panel rounded-[14px] px-4 py-4">
      <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className={`mt-2 font-semibold ${compact ? "text-sm leading-snug" : "font-mono text-3xl"} ${accent ? "text-[hsl(var(--knd-amber))]" : "text-foreground"}`}>
        {value}
        {sub ? <span className="ml-2 text-sm text-muted-foreground">{sub}</span> : null}
      </div>
    </div>
  );
}
