"use client";

import { useState } from "react";
import { colorLetters, type CommanderDistEntry, type PodData, type TournamentDetail } from "@/lib/tournaments";

import Link from "next/link";

type Tab = "Standings" | "Round Story" | "Commanders" | "Bracket";

const pipClasses: Record<string, string> = {
  W: "bg-amber-200/80 text-amber-950",
  U: "bg-sky-500/90 text-white",
  B: "bg-purple-900/90 text-purple-100",
  R: "bg-red-500/90 text-white",
  G: "bg-emerald-500/90 text-white",
};

function Pips({ colors, small = false }: { colors: string; small?: boolean }) {
  return (
    <span className="inline-flex shrink-0 gap-0.5">
      {colorLetters(colors).map((color) => (
        <span
          key={color}
          className={`${small ? "h-4 w-4 text-[9px]" : "h-[18px] w-[18px] text-[10px]"} inline-flex items-center justify-center rounded-full font-semibold ${pipClasses[color] ?? "bg-slate-500 text-white"}`}
        >
          {color}
        </span>
      ))}
    </span>
  );
}

function cutClass(cut: string) {
  if (cut === "Champion") return "border-[hsl(var(--knd-amber))]/35 bg-[hsl(var(--knd-amber))]/10 text-[hsl(var(--knd-amber))]";
  if (cut === "Top 2") return "border-slate-300/20 bg-slate-300/10 text-slate-200";
  if (cut === "Top 4") return "border-primary/25 bg-primary/10 text-primary";
  return "border-border/70 bg-transparent text-muted-foreground";
}

function rankLabel(rank: number) {
  return String(rank);
}

export function TournamentDetailTabs({ tournament }: { tournament: TournamentDetail }) {
  const [active, setActive] = useState<Tab>("Standings");

  const availableTabs: Tab[] = ["Standings"];
  if (tournament.bracketAvailable) availableTabs.push("Round Story");
  availableTabs.push("Commanders");
  if (tournament.bracketAvailable) availableTabs.push("Bracket");

  return (
    <section className="mt-8">
      <div className="flex flex-wrap border-b border-border/70">
        {availableTabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActive(tab)}
            className={`border-b-2 px-5 py-2.5 text-sm transition-colors ${
              active === tab
                ? "border-primary font-semibold text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {active === "Standings" ? <Standings tournament={tournament} /> : null}
        {active === "Round Story" ? <RoundStory tournament={tournament} /> : null}
        {active === "Commanders" ? <Commanders tournament={tournament} /> : null}
        {active === "Bracket" ? <Bracket tournament={tournament} /> : null}
      </div>
    </section>
  );
}

function Standings({ tournament }: { tournament: TournamentDetail }) {
  return (
    <div className="knd-panel overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border/70 text-left font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground whitespace-nowrap">
            <th className="px-4 py-3">#</th>
            <th className="px-3 py-3">Player</th>
            <th className="px-3 py-3">Commander</th>
            <th className="px-3 py-3">Record</th>
            <th className="hidden sm:table-cell px-3 py-3 text-right">Pts</th>
            <th className="hidden sm:table-cell px-4 py-3 text-right">Cut</th>
          </tr>
        </thead>
        <tbody>
          {tournament.standings.map((row) => (
            <tr
              key={`${row.rank}-${row.player}`}
              onClick={(e) => {
                if ((e.target as HTMLElement).closest('a')) return;
                if (row.decklistUrl) window.open(row.decklistUrl, '_blank', 'noreferrer');
              }}
              className={`border-b border-border/60 transition-colors ${row.decklistUrl ? "cursor-pointer hover:bg-accent/40" : "hover:bg-accent/20"} ${
                row.rank === 1 ? "bg-[hsl(var(--knd-amber))]/[0.06]" : ""
              }`}
            >
              <td className="px-4 py-3 font-mono text-sm font-semibold text-muted-foreground">
                {rankLabel(row.rank)}
              </td>
              <td className="px-3 py-3">
                {row.topdeckId ? (
                  <Link
                    href={`/regional-elo/player/${row.topdeckId}`}
                    className="font-medium text-foreground transition-colors hover:text-primary relative z-10"
                  >
                    {row.player}
                  </Link>
                ) : (
                  <div className="font-medium text-foreground">{row.player}</div>
                )}
                {row.team ? <div className="font-mono text-[11px] text-muted-foreground">{row.team}</div> : null}
              </td>
              <td className="px-3 py-3">
                <div className="flex items-center gap-2">
                  <Pips colors={row.colors} small />
                  <span className="text-muted-foreground">{row.commander}</span>
                </div>
              </td>
              <td className="px-3 py-3 font-mono text-[13px] whitespace-nowrap">
                <span className="font-semibold text-primary">{row.wins}</span>
                <span className="text-muted-foreground">-</span>
                <span className="text-red-300">{row.losses}</span>
                <span className="text-muted-foreground">-</span>
                <span className="text-[hsl(var(--knd-amber))]">{row.draws}</span>
              </td>
              <td className="hidden sm:table-cell px-3 py-3 text-right font-mono font-semibold whitespace-nowrap">
                {row.points}
              </td>
              <td className="hidden sm:table-cell px-4 py-3 text-right whitespace-nowrap">
                <span className={`inline-flex rounded-full border px-2 py-1 font-mono text-[11px] ${cutClass(row.cut)}`}>
                  {row.cut}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t border-border/60 px-4 py-3 font-mono text-[11px] text-muted-foreground">
        Top {tournament.cutSize} of {tournament.players} · Pts as reported by the tournament organizer (scoring varies by event)
      </div>
    </div>
  );
}

function RoundStory({ tournament }: { tournament: TournamentDetail }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_310px]">
      <div className="relative space-y-4 pl-12 before:absolute before:left-6 before:top-3 before:h-full before:w-px before:bg-gradient-to-b before:from-primary/40 before:to-primary/5">
        {tournament.narratives.map((stage) => (
          <article
            key={stage.stageNum}
            className={`knd-panel relative rounded-[14px] p-4 ${
              stage.isChamp ? "border-[hsl(var(--knd-amber))]/40 bg-[hsl(var(--knd-amber))]/10" : ""
            }`}
          >
            <span className={`absolute -left-[38px] top-4 flex h-6 w-6 items-center justify-center rounded-full border-2 font-mono text-[10px] ${
              stage.isChamp
                ? "border-[hsl(var(--knd-amber))] bg-[hsl(var(--knd-amber))] text-background"
                : "border-primary/50 bg-card text-primary"
            }`}>
              {stage.stageNum}
            </span>
            <div className="flex gap-4">
              <div className="min-w-0 flex-1">
                <h3 className="text-[15px] font-semibold">{stage.stageLabel}</h3>
                <p className="font-mono text-[11px] text-muted-foreground">{stage.roundRange}</p>
              </div>
              <div className="text-right">
                <div className={`font-mono text-xl font-semibold ${stage.isChamp ? "text-[hsl(var(--knd-amber))]" : "text-primary"}`}>
                  {stage.stat}
                </div>
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{stage.statLabel}</div>
              </div>
            </div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{stage.narrative}</p>
            {stage.spotlight ? (
              <div className={`mt-4 border-l-[3px] px-3 py-2 text-sm ${
                stage.isChamp ? "border-[hsl(var(--knd-amber))] bg-[hsl(var(--knd-amber))]/10" : "border-primary bg-primary/10"
              }`}>
                <span className="mr-2 font-mono text-primary">{stage.spotlightIcon}</span>
                {stage.spotlight}
              </div>
            ) : null}
          </article>
        ))}
      </div>

      <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <div className="knd-panel border-[hsl(var(--knd-amber))]/30 p-4">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[hsl(var(--knd-amber))]">Champion&apos;s Path</div>
          <h3 className="mt-3 text-base font-semibold">{tournament.winner}</h3>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <Pips colors={tournament.winnerColors} small />
            {tournament.winnerCmd}
          </div>
          <div className="mt-4 space-y-2">
            <PathRow label="Swiss" value={tournament.narratives[0]?.stat ?? "—"} />
            <PathRow label={`Top ${tournament.cutSize}`} value="Pod win" />
            <PathRow label="Top 16" value="Pod win" />
            <PathRow label="Final" value="Pod win" />
          </div>
        </div>

        <div className="knd-panel p-4">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Final Pod</div>
          <div className="mt-3 space-y-3">
            {tournament.bracket.t4.players.map((player, index) => (
              <div key={`${player.name}-${index}`} className="flex min-w-0 items-center gap-2">
                <span className="w-7 font-mono text-[11px] text-muted-foreground">{index + 1}</span>
                <Pips colors={player.colors} small />
                <span className={`truncate text-sm ${player.isWinner ? "font-semibold text-[hsl(var(--knd-amber))]" : "text-muted-foreground"}`}>
                  {player.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}

function PathRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-xs font-semibold text-primary">{value}</span>
    </div>
  );
}

function Commanders({ tournament }: { tournament: TournamentDetail }) {
  const maxTotal = Math.max(...tournament.topCutDist.map((r) => r.totalCount), 1);

  const BarRow = ({ row }: { row: CommanderDistEntry }) => (
    <div className="grid grid-cols-[minmax(0,1fr)_1fr_40px] sm:grid-cols-[minmax(200px,400px)_1fr_60px] items-center gap-3 sm:gap-4 border-b border-border/60 px-4 sm:px-5 py-3 transition-colors hover:bg-accent/20">
      <div className="flex items-center gap-2 min-w-0">
        <div className="shrink-0">
          <Pips colors={row.colors} small />
        </div>
        <span className="text-sm font-medium truncate" title={row.name}>{row.name}</span>
      </div>
      <div className="flex h-1.5 w-full rounded-full bg-muted/50 overflow-hidden">
        <div className="h-full bg-primary/80 transition-all" style={{ width: `${(row.cutCount / maxTotal) * 100}%` }} title={`Made Cut: ${row.cutCount}`} />
        <div className="h-full bg-muted-foreground/30 transition-all" style={{ width: `${(row.missCount / maxTotal) * 100}%` }} title={`Missed Cut: ${row.missCount}`} />
      </div>
      <div className="text-right font-mono text-xs">
        <span className="text-primary font-semibold" title="Made Cut">{row.cutCount}</span>
        <span className="text-muted-foreground/60" title="Total Played">/{row.totalCount}</span>
      </div>
    </div>
  );

  return (
    <div className="knd-panel overflow-hidden">
      <div className="border-b border-border/70 px-5 py-4">
        <h3 className="font-semibold">Tournament Meta Representation</h3>
        <p className="text-sm text-muted-foreground">Top-performing commanders and their cut conversion rates</p>
      </div>
      {tournament.topCutDist.map((row) => (
        <BarRow key={row.name} row={row} />
      ))}
      <div className="px-5 py-3 font-mono text-[11px] text-muted-foreground">
        Stacked bars show players who made the cut vs missed.
      </div>
    </div>
  );
}

function Bracket({ tournament }: { tournament: TournamentDetail }) {
  if (tournament.bracketAvailable === false) {
    return (
      <div className="knd-panel p-6">
        <h3 className="text-lg font-semibold">Bracket data not reconstructed yet</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Full standings and decklist links are loaded for this event. Pod-by-pod bracket reconstruction is only shown when reliable bracket data is available.
        </p>
        <a
          href={tournament.source}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-flex text-sm font-medium text-primary transition-colors hover:text-foreground"
        >
          Open source event
        </a>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto pb-3">
      {/* Stages stack vertically below md:; the wide five-column bracket
          scrolls horizontally from md: up. */}
      <div className="flex flex-col gap-6 md:min-w-[1180px] md:flex-row md:items-start md:gap-4">
        <BracketSummary tournament={tournament} />
        <BracketColumn title="Top 40" className="w-full md:w-[340px] grid-cols-2" pods={tournament.bracket.t40} compact />
        <BracketColumn title="Top 16" className="w-full md:w-[218px] grid-cols-1" pods={tournament.bracket.t16} />
        <div className="w-full shrink-0 md:w-[222px]">
          <h3 className="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Top 4</h3>
          <PodCard pod={{ num: 1, players: tournament.bracket.t4.players }} finalPod />
        </div>
        <div className="knd-panel w-full shrink-0 border-[hsl(var(--knd-amber))]/35 bg-[hsl(var(--knd-amber))]/10 p-4 text-center md:w-[162px]">
          <div className="text-3xl text-[hsl(var(--knd-amber))]">★</div>
          <div className="mt-2 text-sm font-semibold text-[hsl(var(--knd-amber))]">{tournament.winner}</div>
          <div className="mt-2 flex justify-center">
            <Pips colors={tournament.winnerColors} small />
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground">{tournament.winnerCmd}</div>
        </div>
      </div>
      <p className="mt-4 font-mono text-[11px] text-muted-foreground">
        ★ amber = pod winner advancing to next stage · cEDH brackets are pods of 4, not 1v1 trees.
      </p>
    </div>
  );
}

function BracketSummary({ tournament }: { tournament: TournamentDetail }) {
  return (
    <div className="knd-panel w-full shrink-0 p-4 md:w-[168px]">
      <h3 className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Swiss</h3>
      <div className="mt-4 space-y-3">
        <PathRow label="Players" value={tournament.players.toLocaleString()} />
        <PathRow label="Top seed" value={tournament.bracket.swiss.topRecord} />
        <PathRow label="Cut" value={`Top ${tournament.cutSize}`} />
      </div>
    </div>
  );
}

function BracketColumn({ title, className, pods, compact = false }: { title: string; className: string; pods: TournamentDetail["bracket"]["t40"]; compact?: boolean }) {
  return (
    <div className={`${className} shrink-0`}>
      <h3 className="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{title}</h3>
      <div className={`grid gap-2 ${className.includes("grid-cols-2") ? "grid-cols-2" : "grid-cols-1"}`}>
        {pods.map((pod) => (
          <PodCard key={pod.num} pod={pod} compact={compact} />
        ))}
      </div>
    </div>
  );
}

function PodCard({ pod, compact = false, finalPod = false }: { pod: PodData; compact?: boolean; finalPod?: boolean }) {
  return (
    <div className={`knd-panel rounded-[10px] p-3 ${finalPod ? "border-[hsl(var(--knd-amber))]/35" : ""}`}>
      <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">P{pod.num}</div>
      <div className="space-y-2">
        {pod.players.map((player, index) => (
          <div key={`${player.name}-${index}`} className="min-w-0">
            <div className={`truncate text-[11px] ${player.isWinner ? "font-semibold text-[hsl(var(--knd-amber))]" : "text-muted-foreground"}`}>
              {player.isWinner ? "★ " : ""}{player.name}
            </div>
            {!compact ? <div className="truncate text-[10px] text-muted-foreground/70">{player.cmd}</div> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
