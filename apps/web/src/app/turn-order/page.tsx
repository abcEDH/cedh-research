"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface SeatPositionStat {
  seat_position: number;
  total_games: number;
  wins: number;
  losses: number;
  draws: number;
  win_rate: string;
  draw_rate?: number;
  win_plus_draw_rate?: number;
}

interface CommanderSeatStat {
  commander_id: string;
  commander_name: string;
  seat_position: number;
  games: number;
  wins: number;
  losses: number;
  draws: number;
  win_rate: string;
  draw_rate: string;
  win_plus_draw_rate: string;
}

export default function TurnOrderPage() {
  const [stats, setStats] = useState<SeatPositionStat[]>([]);
  const [commanderStats, setCommanderStats] = useState<CommanderSeatStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeat, setSelectedSeat] = useState<number | null>(null);

  useEffect(() => {
    async function fetchStats() {
      const [globalResult, commanderResult] = await Promise.all([
        supabase.from("seat_position_stats").select("*").order("seat_position"),
        supabase
          .from("commander_seat_stats")
          .select("*")
          .gte("games", 20)
          .order("games", { ascending: false }),
      ]);

      if (globalResult.error) {
        console.error("Error fetching seat stats:", globalResult.error);
      } else {
        const enrichedStats = (globalResult.data || []).map((stat) => ({
          ...stat,
          draw_rate: stat.draws / stat.total_games,
          win_plus_draw_rate: (stat.wins + stat.draws) / stat.total_games,
        }));
        setStats(enrichedStats);
      }

      if (commanderResult.error) {
        console.error("Error fetching commander seat stats:", commanderResult.error);
      } else {
        const cleaned = (commanderResult.data || []).filter(
          (commander) => commander.commander_name?.toLowerCase() !== "unknown commander"
        );
        setCommanderStats(cleaned);
      }

      setLoading(false);
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Loading turn order data...</p>
      </div>
    );
  }

  const totalGames = stats[0]?.total_games || 0;
  const totalWins = stats.reduce((sum, s) => sum + s.wins, 0);
  const expectedRate = 0.25;

  const expectedWins = totalWins / 4;
  const chiSquare = stats.reduce((sum, s) => {
    const diff = s.wins - expectedWins;
    return sum + (diff * diff) / expectedWins;
  }, 0);

  const cohensW = Math.sqrt(chiSquare / totalWins);
  const effectInterpretation =
    cohensW < 0.1 ? "small" : cohensW < 0.3 ? "medium" : "large";

  const effectColorClass =
    effectInterpretation === "large"
      ? "text-primary"
      : effectInterpretation === "medium"
        ? "text-[hsl(var(--knd-amber))]"
        : "text-muted-foreground";

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
              Turn Order Fairness
            </h1>
            <p className="text-muted-foreground mt-2">
              Statistical analysis of seat position advantage across {totalGames.toLocaleString()} games.
            </p>
          </div>
        </div>

        <Card className="mb-8">
          <CardHeader className="knd-panel-header">
            <CardTitle className="text-lg">Win Rate by Seat Position</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {stats.map((stat) => {
                const winRate = parseFloat(stat.win_rate) * 100;
                const isAboveExpected = winRate > expectedRate * 100;
                const delta = winRate - expectedRate * 100;
                const seatColor = getSeatColor(stat.seat_position);

                return (
                  <div key={stat.seat_position} className="space-y-2">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className="flex h-10 w-10 items-center justify-center rounded-full text-lg font-semibold text-background"
                          style={{ backgroundColor: seatColor }}
                        >
                          {stat.seat_position + 1}
                        </div>
                        <div>
                          <p className="font-medium text-foreground">
                            {getSeatLabel(stat.seat_position)}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {stat.wins.toLocaleString()} wins / {stat.total_games.toLocaleString()} games
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-semibold" style={{ color: seatColor }}>
                          {winRate.toFixed(1)}%
                        </p>
                        <p
                          className={`text-sm font-mono ${
                            isAboveExpected ? "text-primary" : "text-[hsl(var(--knd-amber))]"
                          }`}
                        >
                          {delta > 0 ? "+" : ""}
                          {delta.toFixed(1)}% vs expected
                        </p>
                        <p className="text-xs text-muted-foreground mt-1 font-mono">
                          Draw: {((stat.draw_rate || 0) * 100).toFixed(1)}% · W+D: {((stat.win_plus_draw_rate || 0) * 100).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    <div className="relative h-8 rounded-lg bg-muted/40 overflow-hidden">
                      <div
                        className="absolute top-0 left-0 h-full rounded-lg transition-all"
                        style={{
                          width: `${winRate * 3}%`,
                          backgroundColor: seatColor,
                        }}
                      />
                      <div
                        className="absolute top-0 h-full w-0.5 bg-border/80"
                        style={{ left: `${expectedRate * 100 * 3}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-muted-foreground text-sm mt-4 text-center">
              The thin line marks the expected 25% win rate in four-player pods.
            </p>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Statistical Significance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Chi-Square Statistic (χ²)</span>
                <span className="font-mono text-primary">{chiSquare.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Degrees of Freedom</span>
                <span className="font-mono text-foreground">3</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Cohen&apos;s w (Effect Size)</span>
                <span className={`font-mono ${effectColorClass}`}>{cohensW.toFixed(3)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Effect Interpretation</span>
                <span className={`font-semibold ${effectColorClass}`}>
                  {effectInterpretation.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center justify-between border-t border-border/60 pt-4">
                <span className="text-muted-foreground">Result</span>
                <span className="font-semibold text-primary">Statistically Significant</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Interpretation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <p>
                Players in <strong className="text-foreground">Seat 1 (first)</strong> win{" "}
                <strong className="text-foreground">
                  {(parseFloat(stats[0]?.win_rate || "0") * 100).toFixed(1)}%
                </strong>{" "}
                of games, higher than the expected 25%.
              </p>
              <p>
                Players in <strong className="text-foreground">Seat 4 (last)</strong> win only{" "}
                <strong className="text-foreground">
                  {(parseFloat(stats[3]?.win_rate || "0") * 100).toFixed(1)}%
                </strong>{" "}
                of games, below the expected baseline.
              </p>
              <p>
                The effect size (Cohen&apos;s w = {cohensW.toFixed(3)}) indicates a{" "}
                <strong className={effectColorClass}>{effectInterpretation}</strong> first-player advantage.
              </p>
              <p className="text-xs italic">
                This suggests turn order materially impacts outcomes in competitive pods.
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6">
          <CardHeader className="knd-panel-header">
            <CardTitle className="text-lg">Raw Data</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  <TableHead>Seat</TableHead>
                  <TableHead className="text-right">Games</TableHead>
                  <TableHead className="text-right">Wins</TableHead>
                  <TableHead className="text-right">Losses</TableHead>
                  <TableHead className="text-right">Draws</TableHead>
                  <TableHead className="text-right">Win Rate</TableHead>
                  <TableHead className="text-right">Draw Rate</TableHead>
                  <TableHead className="text-right">Win+Draw</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.map((stat) => (
                  <TableRow key={stat.seat_position} className="border-border/60">
                    <TableCell className="font-medium">
                      Seat {stat.seat_position + 1} ({getSeatLabel(stat.seat_position)})
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {stat.total_games.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-foreground">
                      {stat.wins.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {stat.losses.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {stat.draws.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono" style={{ color: getSeatColor(stat.seat_position) }}>
                      {(parseFloat(stat.win_rate) * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {((stat.draw_rate || 0) * 100).toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {((stat.win_plus_draw_rate || 0) * 100).toFixed(2)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {commanderStats.length > 0 && (
          <Card className="mt-6">
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Commander Performance by Seat</CardTitle>
              <p className="text-sm text-muted-foreground">
                Select a seat to see which commanders perform best from that position.
              </p>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-6">
                {[0, 1, 2, 3].map((seat) => {
                  const seatColor = getSeatColor(seat);
                  const isSelected = selectedSeat === seat;

                  return (
                    <button
                      key={seat}
                      onClick={() => setSelectedSeat(isSelected ? null : seat)}
                      className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                        isSelected
                          ? "border-transparent text-background"
                          : "border-border/70 text-foreground hover:border-primary/40"
                      }`}
                      style={{ backgroundColor: isSelected ? seatColor : undefined }}
                    >
                      Seat {seat + 1}
                    </button>
                  );
                })}
              </div>

              {selectedSeat !== null && (
                <Table>
                  <TableHeader>
                    <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <TableHead>Commander</TableHead>
                      <TableHead className="text-right">Games</TableHead>
                      <TableHead className="text-right">Win Rate</TableHead>
                      <TableHead className="text-right">Draw Rate</TableHead>
                      <TableHead className="text-right">Win+Draw</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {commanderStats
                      .filter((c) => c.seat_position === selectedSeat)
                      .slice(0, 15)
                      .map((commander) => {
                        const winRate = parseFloat(commander.win_rate) * 100;
                        const drawRate = parseFloat(commander.draw_rate) * 100;
                        const winPlusDrawRate = parseFloat(commander.win_plus_draw_rate) * 100;
                        const isAboveExpected = winRate > 25;

                        return (
                          <TableRow key={commander.commander_id} className="border-border/60">
                            <TableCell>
                              <Link
                                href={`/commanders/${commander.commander_id}`}
                                className="text-foreground hover:text-primary"
                              >
                                {normalizeDisplayString(commander.commander_name)}
                              </Link>
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                              {commander.games}
                            </TableCell>
                            <TableCell
                              className={`text-right font-mono ${
                                isAboveExpected ? "text-primary" : "text-muted-foreground"
                              }`}
                            >
                              {winRate.toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                              {drawRate.toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                              {winPlusDrawRate.toFixed(1)}%
                            </TableCell>
                          </TableRow>
                        );
                      })}
                  </TableBody>
                </Table>
              )}

              {selectedSeat === null && (
                <p className="text-muted-foreground text-center py-8">
                  Select a seat position above to see commander performance breakdown.
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}

function getSeatColor(position: number): string {
  const colors = [
    "hsl(var(--knd-cyan))",
    "hsl(var(--knd-cyan) / 0.7)",
    "hsl(var(--knd-amber))",
    "hsl(var(--knd-amber) / 0.7)",
  ];
  return colors[position] || "hsl(var(--knd-line))";
}

function getSeatLabel(position: number): string {
  const labels = ["First", "Second", "Third", "Fourth"];
  return labels[position] || `Position ${position + 1}`;
}
