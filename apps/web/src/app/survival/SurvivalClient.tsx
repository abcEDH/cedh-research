"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";


interface SurvivalPoint {
  round_number: number;
  players_at_risk: number;
  players_survived: number;
  survival_rate: number;
  cumulative_survival: number;
}

interface SeatSurvivalPoint {
  seat_position: number;
  round_number: number;
  players_at_risk: number;
  players_survived: number;
  survival_rate: number;
  cumulative_survival: number;
}

interface Commander {
  commander_id: string;
  commander_name: string;
  total_entries: number;
}

export default function SurvivalClient() {
  const [commanders, setCommanders] = useState<Commander[]>([]);
  const [selectedCommander, setSelectedCommander] = useState<string>("");
  const searchParams = useSearchParams();
  const [globalSurvival, setGlobalSurvival] = useState<SurvivalPoint[]>([]);
  const [seatSurvival, setSeatSurvival] = useState<SeatSurvivalPoint[]>([]);
  const [commanderSurvival, setCommanderSurvival] = useState<SurvivalPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"global" | "seat" | "commander">("seat");

  // Fetch commanders for dropdown
  useEffect(() => {
    async function fetchCommanders() {
      const { data, error } = await supabase
        .from("commander_stats")
        .select("commander_id, commander_name, total_entries")
        .gt("total_entries", 10)
        .order("total_entries", { ascending: false });

      if (!error && data) {
        setCommanders(data);
      }
    }
    fetchCommanders();
  }, []);

  useEffect(() => {
    const commanderParam = searchParams.get("commander");
    if (commanderParam && commanderParam !== selectedCommander) {
      setSelectedCommander(commanderParam);
      setViewMode("commander");
    }
  }, [searchParams, selectedCommander]);

  // Fetch global and seat survival data
  useEffect(() => {
    async function fetchSurvivalData() {
      setLoading(true);

      const [globalResult, seatResult] = await Promise.all([
        supabase.rpc("get_survival_curve"),
        supabase.from("survival_curves_by_seat").select("*").order("seat_position").order("round_number"),
      ]);

      if (globalResult.error) {
        console.error("Error fetching global survival:", globalResult.error);
      } else {
        setGlobalSurvival(globalResult.data || []);
      }

      if (seatResult.error) {
        console.error("Error fetching seat survival:", seatResult.error);
      } else {
        setSeatSurvival(seatResult.data || []);
      }

      setLoading(false);
    }
    fetchSurvivalData();
  }, []);

  // Fetch commander-specific survival when selected
  useEffect(() => {
    async function fetchCommanderSurvival() {
      if (!selectedCommander) {
        setCommanderSurvival([]);
        return;
      }

      const { data, error } = await supabase.rpc("get_survival_curve", {
        p_commander_id: selectedCommander,
      });

      if (error) {
        console.error("Error fetching commander survival:", error);
        setCommanderSurvival([]);
      } else {
        setCommanderSurvival(data || []);
      }
    }
    fetchCommanderSurvival();
  }, [selectedCommander]);

  // Calculate key metrics
  const getMedianSurvivalRound = (data: SurvivalPoint[]): number | null => {
    const medianPoint = data.find((p) => p.cumulative_survival <= 0.5);
    return medianPoint ? medianPoint.round_number : null;
  };

  const get75thPercentileRound = (data: SurvivalPoint[]): number | null => {
    const point = data.find((p) => p.cumulative_survival <= 0.25);
    return point ? point.round_number : null;
  };

  const globalMedian = getMedianSurvivalRound(globalSurvival);
  const commanderMedian = selectedCommander ? getMedianSurvivalRound(commanderSurvival) : null;

  // Get max rounds for chart scaling
  const maxRounds = Math.max(
    ...globalSurvival.map((p) => p.round_number),
    ...seatSurvival.map((p) => p.round_number),
    ...commanderSurvival.map((p) => p.round_number),
    6
  );

  const selectedCommanderName = commanders.find((c) => c.commander_id === selectedCommander)?.commander_name;
  const displayCommanderName = selectedCommanderName
    ? normalizeDisplayString(selectedCommanderName)
    : null;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
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
              Survival Analysis
            </h1>
            <p className="text-muted-foreground mt-2">
              Track the probability of surviving through each tournament round.
            </p>
          </div>
        </div>

        {/* View Mode Selector */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="flex gap-2">
                <Button
                  variant={viewMode === "seat" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("seat")}
                >
                  By Seat Position
                </Button>
                <Button
                  variant={viewMode === "global" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("global")}
                >
                  Global Average
                </Button>
                <Button
                  variant={viewMode === "commander" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("commander")}
                >
                  By Commander
                </Button>
              </div>

              {viewMode === "commander" && (
                <div className="flex flex-1 items-center gap-4">
                  <select
                    value={selectedCommander}
                    onChange={(e) => setSelectedCommander(e.target.value)}
                    className="knd-input flex-1 max-w-md"
                  >
                    <option value="">Select a commander...</option>
                    {commanders.map((c) => (
                      <option key={c.commander_id} value={c.commander_id}>
                        {normalizeDisplayString(c.commander_name)} ({c.total_entries} entries)
                      </option>
                    ))}
                  </select>
                  {selectedCommander && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedCommander("")}
                    >
                      Clear
                    </Button>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Explanation */}
        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <h3 className="text-lg font-bold text-primary mb-2">
                  What is Survival Analysis?
                </h3>
                <p className="text-muted-foreground text-sm">
                  Survival analysis tracks the probability of &quot;surviving&quot; (not losing) through each
                  tournament round. A player &quot;survives&quot; a round if they win or draw.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-bold text-muted-foreground mb-2">
                  Cumulative Survival
                </h3>
                <p className="text-muted-foreground text-sm">
                  Shows the probability of surviving through round N given the player started
                  in round 1. This compounds each round&apos;s survival rate.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-bold text-primary mb-2">
                  Median Survival
                </h3>
                <p className="text-muted-foreground text-sm">
                  The round at which 50% of players have experienced at least one loss.
                  Lower is worse - it means players lose earlier on average.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {loading ? (
          <div className="text-center py-12 text-muted-foreground">Loading survival data...</div>
        ) : (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <Card className="bg-card/60 border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-muted-foreground text-sm font-medium">
                    Global Median Survival
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-primary">
                    {globalMedian ? `Round ${globalMedian}` : "N/A"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    50% of players have lost by this round
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-card/60 border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-muted-foreground text-sm font-medium">
                    Round 1 Survival
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-primary">
                    {globalSurvival[0]
                      ? `${(globalSurvival[0].survival_rate * 100).toFixed(1)}%`
                      : "N/A"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Win or draw in round 1
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-card/60 border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-muted-foreground text-sm font-medium">
                    75th Percentile Drop
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-[hsl(var(--knd-amber))]">
                    {get75thPercentileRound(globalSurvival)
                      ? `Round ${get75thPercentileRound(globalSurvival)}`
                      : "N/A"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    75% of players have lost by this round
                  </p>
                </CardContent>
              </Card>

              {selectedCommander && commanderSurvival.length > 0 && (
                <Card className="bg-card/60 border-border/60 border-l-4 border-l-[hsl(var(--knd-cyan))]">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-muted-foreground text-sm font-medium">
                      {selectedCommanderName?.split(" / ")[0]} Median
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-bold text-muted-foreground">
                      {commanderMedian ? `Round ${commanderMedian}` : "N/A"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      vs Global: {globalMedian ? `Round ${globalMedian}` : "N/A"}
                    </p>
                  </CardContent>
                </Card>
              )}

              {!selectedCommander && (
                <Card className="bg-card/60 border-border/60">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-muted-foreground text-sm font-medium">
                      Data Points
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-bold text-muted-foreground">
                      {globalSurvival[0]?.players_at_risk.toLocaleString() || "0"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Round 1 participants
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Survival Chart */}
            <Card className="bg-card/60 border-border/60 mb-8">
              <CardHeader>
                <CardTitle className="text-foreground">
                  {viewMode === "seat" && "Survival Curves by Seat Position"}
                  {viewMode === "global" && "Global Survival Curve"}
                  {viewMode === "commander" && (selectedCommander
                    ? `Survival Curve: ${selectedCommanderName}`
                    : "Select a Commander")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {viewMode === "seat" && <SeatSurvivalChart data={seatSurvival} maxRounds={maxRounds} />}
                {viewMode === "global" && <GlobalSurvivalChart data={globalSurvival} maxRounds={maxRounds} />}
                {viewMode === "commander" && (
                  selectedCommander && commanderSurvival.length > 0 ? (
                    <ComparativeSurvivalChart
                      commanderData={commanderSurvival}
                      globalData={globalSurvival}
                      commanderName={displayCommanderName || "Commander"}
                      maxRounds={maxRounds}
                    />
                  ) : (
                    <p className="text-muted-foreground text-center py-12">
                      Select a commander to view their survival curve
                    </p>
                  )
                )}
              </CardContent>
            </Card>

            {/* Data Table */}
            <Card className="bg-card/60 border-border/60">
              <CardHeader>
                <CardTitle className="text-foreground">Raw Survival Data</CardTitle>
              </CardHeader>
              <CardContent>
                {viewMode === "seat" && <SeatSurvivalTable data={seatSurvival} />}
                {viewMode === "global" && <GlobalSurvivalTable data={globalSurvival} />}
                {viewMode === "commander" && selectedCommander && commanderSurvival.length > 0 && (
                  <GlobalSurvivalTable data={commanderSurvival} />
                )}
                {viewMode === "commander" && !selectedCommander && (
                  <p className="text-muted-foreground text-center py-4">
                    Select a commander to view data
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Methodology */}
            <Card className="bg-card/60 border-border/60 mt-8">
              <CardHeader>
                <CardTitle className="text-foreground">Methodology</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground space-y-2">
                <p>
                  <strong className="text-primary">Survival Rate</strong> = (Wins + Draws) / Total Games
                  for each round
                </p>
                <p>
                  <strong className="text-muted-foreground">Cumulative Survival</strong> = Product of all survival
                  rates up to and including the current round (Kaplan-Meier style)
                </p>
                <p className="text-sm italic">
                  Note: Only Swiss rounds are included. Bracket/elimination rounds are excluded as they
                  have different dynamics. Byes are also excluded from calculations.
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

// Visual survival chart using CSS bars (no external charting library needed)
function SeatSurvivalChart({ data, maxRounds }: { data: SeatSurvivalPoint[]; maxRounds: number }) {
  const seatColors = [
    "hsl(var(--knd-cyan))",
    "hsl(var(--knd-cyan) / 0.7)",
    "hsl(var(--knd-amber))",
    "hsl(var(--knd-amber) / 0.7)",
  ];
  const seatLabels = ["Seat 1 (First)", "Seat 2 (Second)", "Seat 3 (Third)", "Seat 4 (Fourth)"];

  // Group by seat
  const bySeat: Map<number, SeatSurvivalPoint[]> = new Map();
  data.forEach((point) => {
    const existing = bySeat.get(point.seat_position) || [];
    existing.push(point);
    bySeat.set(point.seat_position, existing);
  });

  const rounds = Array.from({ length: maxRounds }, (_, i) => i + 1);

  return (
    <div className="space-y-6">
      {/* Legend */}
      <div className="flex flex-wrap gap-4 justify-center">
        {[0, 1, 2, 3].map((seat) => (
          <div key={seat} className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: seatColors[seat] }}
            />
            <span className="text-sm text-muted-foreground">{seatLabels[seat]}</span>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="relative h-64 flex items-end gap-1">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between text-xs text-muted-foreground">
          <span>100%</span>
          <span>75%</span>
          <span>50%</span>
          <span>25%</span>
          <span>0%</span>
        </div>

        {/* Grid lines */}
        <div className="absolute left-12 right-0 top-0 bottom-0 flex flex-col justify-between pointer-events-none">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="border-t border-border/60" />
          ))}
        </div>

        {/* Bars */}
        <div className="flex-1 ml-14 flex items-end gap-2 h-full">
          {rounds.map((round) => (
            <div key={round} className="flex-1 flex flex-col items-center h-full">
              <div className="flex gap-0.5 items-end h-full w-full flex-1">
                {[0, 1, 2, 3].map((seat) => {
                  const seatData = bySeat.get(seat) || [];
                  const roundData = seatData.find((p) => p.round_number === round);
                  const survival = roundData?.cumulative_survival || 0;
                  const height = `${survival * 100}%`;

                  return (
                    <div
                      key={seat}
                      className="flex-1 rounded-t transition-all hover:opacity-80"
                      style={{
                        backgroundColor: seatColors[seat],
                        height,
                        minHeight: survival > 0 ? "2px" : "0",
                      }}
                      title={`Seat ${seat + 1}, Round ${round}: ${(survival * 100).toFixed(1)}%`}
                    />
                  );
                })}
              </div>
              <span className="text-xs text-muted-foreground mt-2">R{round}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 50% line annotation */}
      <p className="text-center text-xs text-muted-foreground">
        Dashed line at 50% indicates median survival threshold
      </p>
    </div>
  );
}

function GlobalSurvivalChart({ data, maxRounds }: { data: SurvivalPoint[]; maxRounds: number }) {
  const rounds = Array.from({ length: maxRounds }, (_, i) => i + 1);

  return (
    <div className="space-y-6">
      {/* Chart */}
      <div className="relative h-64 flex items-end gap-1">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between text-xs text-muted-foreground">
          <span>100%</span>
          <span>75%</span>
          <span>50%</span>
          <span>25%</span>
          <span>0%</span>
        </div>

        {/* Grid lines */}
        <div className="absolute left-12 right-0 top-0 bottom-0 flex flex-col justify-between pointer-events-none">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="border-t border-border/60" />
          ))}
        </div>

        {/* 50% reference line */}
        <div
          className="absolute left-12 right-0 border-t-2 border-dashed border-[hsl(var(--knd-amber))]/50"
          style={{ top: "50%" }}
        />

        {/* Bars */}
        <div className="flex-1 ml-14 flex items-end gap-2 h-full">
          {rounds.map((round) => {
            const roundData = data.find((p) => p.round_number === round);
            const survival = roundData?.cumulative_survival || 0;
            const height = `${survival * 100}%`;
            const isBelow50 = survival < 0.5;

            return (
              <div key={round} className="flex-1 flex flex-col items-center h-full">
                <div className="w-full flex-1 flex items-end">
                  <div
                    className="w-full rounded-t transition-all hover:opacity-80"
                    style={{
                      backgroundColor: isBelow50
                        ? "hsl(var(--knd-amber))"
                        : "hsl(var(--knd-cyan))",
                      height,
                      minHeight: survival > 0 ? "2px" : "0",
                    }}
                    title={`Round ${round}: ${(survival * 100).toFixed(1)}% cumulative survival`}
                  />
                </div>
                <span className="text-xs text-muted-foreground mt-2">R{round}</span>
              </div>
            );
          })}
        </div>
      </div>

      <p className="text-center text-xs text-muted-foreground">
        Dashed orange line at 50% indicates median survival threshold.
        Bars turn red when below 50%.
      </p>
    </div>
  );
}

function ComparativeSurvivalChart({
  commanderData,
  globalData,
  commanderName,
  maxRounds
}: {
  commanderData: SurvivalPoint[];
  globalData: SurvivalPoint[];
  commanderName: string;
  maxRounds: number;
}) {
  const rounds = Array.from({ length: maxRounds }, (_, i) => i + 1);

  return (
    <div className="space-y-6">
      {/* Legend */}
      <div className="flex flex-wrap gap-6 justify-center">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-[hsl(var(--knd-cyan))]" />
          <span className="text-sm text-muted-foreground">{commanderName.split(" / ")[0]}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-muted/30 border border-border/60" />
          <span className="text-sm text-muted-foreground">Global Average</span>
        </div>
      </div>

      {/* Chart */}
      <div className="relative h-64 flex items-end gap-1">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between text-xs text-muted-foreground">
          <span>100%</span>
          <span>75%</span>
          <span>50%</span>
          <span>25%</span>
          <span>0%</span>
        </div>

        {/* Grid lines */}
        <div className="absolute left-12 right-0 top-0 bottom-0 flex flex-col justify-between pointer-events-none">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="border-t border-border/60" />
          ))}
        </div>

        {/* 50% reference line */}
        <div
          className="absolute left-12 right-0 border-t-2 border-dashed border-[hsl(var(--knd-amber))]/50"
          style={{ top: "50%" }}
        />

        {/* Bars */}
        <div className="flex-1 ml-14 flex items-end gap-2 h-full">
          {rounds.map((round) => {
            const cmdData = commanderData.find((p) => p.round_number === round);
            const glbData = globalData.find((p) => p.round_number === round);
            const cmdSurvival = cmdData?.cumulative_survival || 0;
            const glbSurvival = glbData?.cumulative_survival || 0;

            return (
              <div key={round} className="flex-1 flex flex-col items-center h-full">
                <div className="flex gap-1 items-end w-full flex-1">
                  {/* Global bar (background) */}
                  <div
                    className="flex-1 rounded-t transition-all opacity-30 border border-border/60"
                    style={{
                      backgroundColor: "hsl(var(--knd-line))",
                      height: `${glbSurvival * 100}%`,
                      minHeight: glbSurvival > 0 ? "2px" : "0",
                    }}
                    title={`Global Round ${round}: ${(glbSurvival * 100).toFixed(1)}%`}
                  />
                  {/* Commander bar */}
                  <div
                    className="flex-1 rounded-t transition-all hover:opacity-80"
                    style={{
                      backgroundColor:
                        cmdSurvival >= glbSurvival
                          ? "hsl(var(--knd-cyan))"
                          : "hsl(var(--knd-amber))",
                      height: `${cmdSurvival * 100}%`,
                      minHeight: cmdSurvival > 0 ? "2px" : "0",
                    }}
                    title={`${commanderName} Round ${round}: ${(cmdSurvival * 100).toFixed(1)}%`}
                  />
                </div>
                <span className="text-xs text-muted-foreground mt-2">R{round}</span>
              </div>
            );
          })}
        </div>
      </div>

      <p className="text-center text-xs text-muted-foreground">
        Commander bars are green when above global average, red when below.
        Gray bars show global baseline.
      </p>
    </div>
  );
}

function SeatSurvivalTable({ data }: { data: SeatSurvivalPoint[] }) {
  // Group by round
  const rounds = [...new Set(data.map((d) => d.round_number))].sort((a, b) => a - b);
  const seatLabels = ["Seat 1", "Seat 2", "Seat 3", "Seat 4"];
  const seatColors = [
    "hsl(var(--knd-cyan))",
    "hsl(var(--knd-cyan) / 0.7)",
    "hsl(var(--knd-amber))",
    "hsl(var(--knd-amber) / 0.7)",
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border/60">
            <th className="text-left py-2 text-muted-foreground">Round</th>
            {[0, 1, 2, 3].map((seat) => (
              <th
                key={seat}
                className="text-right py-2"
                style={{ color: seatColors[seat] }}
              >
                {seatLabels[seat]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rounds.map((round) => (
            <tr key={round} className="border-b border-border/60">
              <td className="py-2 font-medium">Round {round}</td>
              {[0, 1, 2, 3].map((seat) => {
                const point = data.find((d) => d.round_number === round && d.seat_position === seat);
                return (
                  <td key={seat} className="py-2 text-right font-mono">
                    <span style={{ color: seatColors[seat] }}>
                      {point ? `${(point.cumulative_survival * 100).toFixed(1)}%` : "-"}
                    </span>
                    <span className="text-muted-foreground text-xs ml-1">
                      ({point?.players_at_risk || 0})
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GlobalSurvivalTable({ data }: { data: SurvivalPoint[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border/60">
            <th className="text-left py-2 text-muted-foreground">Round</th>
            <th className="text-right py-2 text-muted-foreground">At Risk</th>
            <th className="text-right py-2 text-muted-foreground">Survived</th>
            <th className="text-right py-2 text-muted-foreground">Round Survival</th>
            <th className="text-right py-2 text-muted-foreground">Cumulative</th>
          </tr>
        </thead>
        <tbody>
          {data.map((point) => {
            const isBelow50 = point.cumulative_survival < 0.5;
            return (
              <tr key={point.round_number} className="border-b border-border/60">
                <td className="py-2 font-medium">Round {point.round_number}</td>
                <td className="py-2 text-right font-mono text-muted-foreground">
                  {point.players_at_risk.toLocaleString()}
                </td>
                <td className="py-2 text-right font-mono text-primary">
                  {point.players_survived.toLocaleString()}
                </td>
                <td className="py-2 text-right font-mono text-primary">
                  {(point.survival_rate * 100).toFixed(1)}%
                </td>
                <td
                  className="py-2 text-right font-mono font-bold"
                  style={{
                    color: isBelow50
                      ? "hsl(var(--knd-amber))"
                      : "hsl(var(--knd-cyan))",
                  }}
                >
                  {(point.cumulative_survival * 100).toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
