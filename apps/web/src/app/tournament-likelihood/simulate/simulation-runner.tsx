"use client";

import { useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type SimulationRow = {
  player_id?: string;
  name: string;
  win_probability?: number;
  top_cut_probability?: number;
  top64_probability?: number;
  top40_probability?: number;
  top16_probability?: number;
  top10_probability?: number;
  top4_probability?: number;
};

type ActivePod = {
  round_number: number;
  table_number: number;
  draw_probability: number;
  players: Array<{
    player_id: string;
    name: string;
    win_probability: number;
    decisive_win_probability?: number;
    seat?: number | null;
  }>;
};

type CompletedPod = {
  round_number: number;
  table_number: number;
  result: string;
  winner_id?: string | null;
  is_draw: boolean;
  players: Array<{
    player_id: string;
    name: string;
    seat?: number | null;
    result: "win" | "loss" | "draw";
  }>;
};

type ProbabilityKey =
  | "win_probability"
  | "top_cut_probability"
  | "top64_probability"
  | "top40_probability"
  | "top16_probability"
  | "top10_probability"
  | "top4_probability";

type SimulationSnapshot = {
  status: "running" | "complete";
  completed: number;
  total: number;
  progress_percent?: number | null;
  simulations_per_second?: number;
  point_requirements?: {
    top_cut?: Array<{ points: number; probability: number; count?: number }>;
    bye?: Array<{ points: number; probability: number; count?: number }>;
  };
  top_win_probabilities?: SimulationRow[];
  top_top_cut_probabilities?: SimulationRow[];
  top_top64_probabilities?: SimulationRow[];
  top_top40_probabilities?: SimulationRow[];
  top_top16_probabilities?: SimulationRow[];
  top_top10_probabilities?: SimulationRow[];
  top_top4_probabilities?: SimulationRow[];
  active_pods?: ActivePod[];
  completed_pods?: CompletedPod[];
};

const MAX_RUN_SECONDS = 10 * 60;

function formatPercent(value: number | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function formatRate(value: number | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return value >= 10 ? value.toFixed(0) : value.toFixed(1);
}

function formatDuration(secondsValue: string, fallbackSeconds: number) {
  const seconds = Number(secondsValue || fallbackSeconds);
  if (!Number.isFinite(seconds) || seconds <= 0) return "default run";
  if (seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
  }
  return `${seconds} seconds`;
}

function normalizeRunSeconds(value: string, fallbackSeconds: number) {
  const parsed = Number(value || fallbackSeconds);
  if (!Number.isInteger(parsed) || parsed < 1) return fallbackSeconds;
  return Math.min(parsed, MAX_RUN_SECONDS);
}

function normalizeOptionalInteger(value: string, min: number) {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= min ? parsed : null;
}

function readProbability(
  row: SimulationRow,
  probabilityKey: ProbabilityKey
) {
  return row[probabilityKey] ?? (probabilityKey.startsWith("top") ? row.top_cut_probability : undefined);
}

function byePointLineTitle(topCutValue: string, fallbackTopCut: number) {
  const parsedTopCut = Number(topCutValue || fallbackTopCut);
  if (parsedTopCut === 10) return "Top 2 (Bye) Point Line";
  if (parsedTopCut === 40) return "Top 8 (Bye) Point Line";
  return "Bye Point Line";
}

function hasByePointLine(topCut: number) {
  return topCut === 10 || topCut === 40;
}

function advancementOddsCards(topCut: number) {
  if (topCut === 40 || topCut === 64) return [4, 16, topCut];
  if (topCut > 4) return [4, topCut];
  return topCut > 0 ? [topCut] : [];
}

function advancementProbabilityKey(cutSize: number): ProbabilityKey {
  return `top${cutSize}_probability` as ProbabilityKey;
}

function advancementRows(
  snapshot: SimulationSnapshot | null,
  cutSize: number,
  topCut: number
): SimulationRow[] | undefined {
  if (cutSize === 64) return snapshot?.top_top64_probabilities;
  if (cutSize === 40) return snapshot?.top_top40_probabilities;
  if (cutSize === 16) return snapshot?.top_top16_probabilities;
  if (cutSize === 10) return snapshot?.top_top10_probabilities;
  if (cutSize === 4) return snapshot?.top_top4_probabilities;
  return cutSize === topCut ? snapshot?.top_top_cut_probabilities : undefined;
}

function ProbabilityTable({
  rows,
  probabilityKey,
  search,
}: {
  rows: SimulationRow[] | undefined;
  probabilityKey: ProbabilityKey;
  search: string;
}) {
  const normalizedSearch = search.trim().toLowerCase();
  const filteredRows = normalizedSearch
    ? (rows ?? []).filter((row) => row.name.toLowerCase().includes(normalizedSearch))
    : rows ?? [];
  const visibleRows = filteredRows.slice(0, 20);
  if (visibleRows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {normalizedSearch ? "No matching players in this odds table." : "Waiting for the first simulation result."}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[420px] text-left text-sm">
        <thead className="border-b border-border/60 text-xs uppercase tracking-[0.24em] text-muted-foreground">
          <tr>
            <th className="px-2 py-3">Player</th>
            <th className="px-2 py-3 text-right">Probability</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/40">
          {visibleRows.map((row) => (
            <tr key={`${probabilityKey}-${row.name}`}>
              <td className="px-2 py-3 text-foreground">{row.name}</td>
              <td className="px-2 py-3 text-right text-foreground">{formatPercent(readProbability(row, probabilityKey))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PointLineTable({
  rows,
}: {
  rows: Array<{ points: number; probability: number; count?: number }> | undefined;
}) {
  const visibleRows = rows ?? [];
  if (visibleRows.length === 0) {
    return <p className="text-sm text-muted-foreground">Waiting for point-line results.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[320px] text-left text-sm">
        <thead className="border-b border-border/60 text-xs uppercase tracking-[0.24em] text-muted-foreground">
          <tr>
            <th className="px-2 py-3">Points</th>
            <th className="px-2 py-3 text-right">Probability</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/40">
          {visibleRows.map((row) => (
            <tr key={`points-${row.points}`}>
              <td className="px-2 py-3 text-foreground">{row.points}</td>
              <td className="px-2 py-3 text-right text-foreground">{formatPercent(row.probability)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function podCardClass(kind: "active" | "completed", pod: ActivePod | CompletedPod) {
  if (kind === "completed" && (pod as CompletedPod).is_draw) {
    return "rounded-md border border-slate-500/40 bg-slate-500/10 p-4";
  }
  return "rounded-md border border-border/60 bg-muted/20 p-4";
}

function completedPlayerRowClass(result: CompletedPod["players"][number]["result"]) {
  if (result === "win") {
    return "bg-emerald-500/15 text-emerald-100";
  }
  return "text-foreground";
}

function podIdentityKey(kind: "active" | "completed", pod: ActivePod | CompletedPod, index: number) {
  const playerKey = pod.players.map((player) => player.player_id).sort().join("-");
  return `${kind}-${pod.round_number}-${pod.table_number}-${playerKey || index}`;
}

function CurrentRoundPodsTable({
  activePods,
  completedPods,
}: {
  activePods: ActivePod[] | undefined;
  completedPods: CompletedPod[] | undefined;
}) {
  const visiblePods = [
    ...(completedPods ?? []).map((pod) => ({ kind: "completed" as const, pod })),
    ...(activePods ?? []).map((pod) => ({ kind: "active" as const, pod })),
  ].sort((left, right) => {
    if (left.pod.round_number !== right.pod.round_number) {
      return left.pod.round_number - right.pod.round_number;
    }
    return left.pod.table_number - right.pod.table_number;
  });
  if (visiblePods.length === 0) return null;

  return (
    <Card className="knd-panel">
      <CardHeader>
        <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
          Current Round Pods
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 xl:grid-cols-2">
          {visiblePods.map(({ kind, pod }, index) => {
            const isCompleted = kind === "completed";
            return (
              <div
                className={podCardClass(kind, pod)}
                key={podIdentityKey(kind, pod, index)}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      Round {pod.round_number}
                    </p>
                    <p className="mt-1 text-base font-semibold text-foreground">
                      Table {pod.table_number}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      {isCompleted ? "Result" : "Draw"}
                    </p>
                    <p className="mt-1 text-base font-semibold text-primary">
                      {isCompleted
                        ? (pod as CompletedPod).is_draw
                          ? "Draw"
                          : `${(pod as CompletedPod).result} won`
                        : formatPercent((pod as ActivePod).draw_probability)}
                    </p>
                  </div>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border/60 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      <tr>
                        <th className="px-2 py-2">Player</th>
                        <th className="px-2 py-2 text-right">{isCompleted ? "Result" : "Win"}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {pod.players.map((player) => (
                        <tr
                          className={
                            isCompleted
                              ? completedPlayerRowClass((player as CompletedPod["players"][number]).result)
                              : "text-foreground"
                          }
                          key={player.player_id}
                        >
                          <td className="px-2 py-2">
                            {player.seat ? `Seat ${player.seat} · ` : ""}
                            {player.name}
                          </td>
                          <td className="px-2 py-2 text-right">
                            {isCompleted
                              ? (player as CompletedPod["players"][number]).result.toUpperCase()
                              : formatPercent((player as ActivePod["players"][number]).win_probability)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export function SimulationRunner({
  defaultSwissRounds,
  defaultTopCut,
  defaultRunSeconds,
  defaultDropAfterRound,
  defaultDropMinPoints,
  playerCount,
  slug,
}: {
  defaultSwissRounds: number;
  defaultTopCut: number;
  defaultRunSeconds: number;
  defaultDropAfterRound: number | null;
  defaultDropMinPoints: number | null;
  playerCount: number;
  slug: string;
}) {
  const [swissRounds, setSwissRounds] = useState(String(defaultSwissRounds));
  const [topCut, setTopCut] = useState(String(defaultTopCut));
  const [runSeconds, setRunSeconds] = useState(String(defaultRunSeconds));
  const [dropAfterRound, setDropAfterRound] = useState(
    defaultDropAfterRound === null ? "" : String(defaultDropAfterRound)
  );
  const [dropMinPoints, setDropMinPoints] = useState(
    defaultDropMinPoints === null ? "" : String(defaultDropMinPoints)
  );
  const [snapshot, setSnapshot] = useState<SimulationSnapshot | null>(null);
  const [oddsSearch, setOddsSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  const selectedRunSeconds = normalizeRunSeconds(runSeconds, defaultRunSeconds);

  const progressPercent = useMemo(() => {
    if (typeof snapshot?.progress_percent === "number") {
      return Math.min(Math.max(snapshot.progress_percent, 0), 100);
    }
    if (!snapshot?.total) return 0;
    return Math.min((snapshot.completed / snapshot.total) * 100, 100);
  }, [snapshot]);
  const selectedTopCut = Number(topCut || defaultTopCut);
  const selectedDropAfterRound = normalizeOptionalInteger(dropAfterRound, 1);
  const selectedDropMinPoints = normalizeOptionalInteger(dropMinPoints, 0);
  const hasDropRule = selectedDropAfterRound !== null && selectedDropMinPoints !== null;

  function startSimulation() {
    sourceRef.current?.close();
    setSnapshot(null);
    setError(null);
    setIsRunning(true);

    const params = new URLSearchParams({
      tournament: slug,
      swissRounds: swissRounds || String(defaultSwissRounds),
      topCut: topCut || String(defaultTopCut),
      runSeconds: String(selectedRunSeconds),
    });
    if (hasDropRule) {
      params.set("dropAfterRound", String(selectedDropAfterRound));
      params.set("dropMinPoints", String(selectedDropMinPoints));
    }
    const source = new EventSource(`/tournament-likelihood/simulate/stream?${params.toString()}`);
    sourceRef.current = source;

    source.onmessage = (event) => {
      const nextSnapshot = JSON.parse(event.data) as SimulationSnapshot;
      setSnapshot(nextSnapshot);
      if (nextSnapshot.status === "complete") {
        setIsRunning(false);
        source.close();
      }
    };

    source.onerror = () => {
      setError("Simulation stream failed.");
      setIsRunning(false);
      source.close();
    };
  }

  return (
    <>
      <Card className="knd-panel mt-8">
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
            Simulation Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr_1fr_1fr_auto]">
            <label className="flex flex-col gap-2 text-sm text-muted-foreground">
              Swiss rounds
              <input
                className="knd-input"
                min={1}
                onChange={(event) => setSwissRounds(event.target.value)}
                type="number"
                value={swissRounds}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted-foreground">
              Cut to
              <input
                className="knd-input"
                min={0}
                onChange={(event) => setTopCut(event.target.value)}
                type="number"
                value={topCut}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted-foreground">
              Run time (seconds)
              <input
                className="knd-input"
                max={MAX_RUN_SECONDS}
                min={1}
                onChange={(event) => setRunSeconds(event.target.value)}
                placeholder={String(defaultRunSeconds)}
                type="number"
                value={runSeconds}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted-foreground">
              Drop after round
              <input
                className="knd-input"
                min={1}
                onChange={(event) => setDropAfterRound(event.target.value)}
                placeholder="Optional"
                type="number"
                value={dropAfterRound}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-muted-foreground">
              Minimum points
              <input
                className="knd-input"
                min={0}
                onChange={(event) => setDropMinPoints(event.target.value)}
                placeholder="Optional"
                type="number"
                value={dropMinPoints}
              />
            </label>
            <div className="flex items-end">
              <button
                className="knd-chip border border-border/70 px-4 py-3 text-sm text-foreground transition hover:text-primary disabled:pointer-events-none disabled:opacity-50"
                disabled={isRunning}
                onClick={startSimulation}
                type="button"
              >
                {isRunning ? "Running..." : "Run Simulation"}
              </button>
            </div>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            {playerCount ? `${playerCount} players · ` : ""}
            {swissRounds || defaultSwissRounds} Swiss rounds ·{" "}
            {Number(topCut || defaultTopCut) > 0 ? `Cut to Top ${topCut || defaultTopCut}` : "No top cut"} ·{" "}
            {hasDropRule
              ? `Drop players below ${selectedDropMinPoints} points after round ${selectedDropAfterRound} · `
              : "No point drop · "}
            Runs for {formatDuration(String(selectedRunSeconds), defaultRunSeconds)}.
          </p>
          {(isRunning || snapshot) && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs uppercase tracking-[0.24em] text-muted-foreground">
                <span>{progressPercent.toFixed(1)}% complete</span>
                <span>
                  {snapshot?.status === "complete" ? "Complete" : "Running"}
                  {snapshot ? ` · ${formatRate(snapshot.simulations_per_second)} sims/sec` : ""}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded bg-muted">
                <div className="h-full bg-primary transition-all" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <div className="mt-6 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        {snapshot?.active_pods?.length || snapshot?.completed_pods?.length ? (
          <div className="xl:col-span-2">
            <CurrentRoundPodsTable
              activePods={snapshot.active_pods}
              completedPods={snapshot.completed_pods}
            />
          </div>
        ) : null}

        <Card className="knd-panel">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              {selectedTopCut > 0 ? `Top ${selectedTopCut} Point Line` : "Top Cut Point Line"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PointLineTable rows={snapshot?.point_requirements?.top_cut} />
          </CardContent>
        </Card>

        <Card className="knd-panel">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Search
            </CardTitle>
          </CardHeader>
          <CardContent>
            <input
              className="knd-input"
              onChange={(event) => setOddsSearch(event.target.value)}
              placeholder="Filter by player"
              type="search"
              value={oddsSearch}
            />
          </CardContent>
        </Card>

        {hasByePointLine(selectedTopCut) && (
          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                {byePointLineTitle(topCut, defaultTopCut)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <PointLineTable rows={snapshot?.point_requirements?.bye} />
            </CardContent>
          </Card>
        )}

        <Card className="knd-panel">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Winner Odds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ProbabilityTable
              probabilityKey="win_probability"
              rows={snapshot?.top_win_probabilities}
              search={oddsSearch}
            />
          </CardContent>
        </Card>

        {advancementOddsCards(selectedTopCut).map((cutSize) => (
          <Card className="knd-panel" key={`top-${cutSize}-odds`}>
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                Top {cutSize} Odds
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ProbabilityTable
                probabilityKey={advancementProbabilityKey(cutSize)}
                rows={advancementRows(snapshot, cutSize, selectedTopCut)}
                search={oddsSearch}
              />
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
