import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default function LimitationsPage() {
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <div className="knd-watermark absolute inset-0" />
          <div className="relative">
            <Link href="/about" className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to Methodology
            </Link>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              Data Limitations
            </h1>
            <p className="text-muted-foreground mt-2">
              Notes on how to interpret metrics and where the data can be misleading.
            </p>
          </div>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Top 16 vs Top 10/Top 4 Cutoffs</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-3">
              <p>
                Some events use a Top 10 cutoff when attendance is under 64 players. For very small events
                (34 players or fewer), we only count Top 4 finishes to avoid inflating conversion rates.
              </p>
              <p>
                When comparing commanders across events of different sizes, treat the Top 16/Top 10/Top 4
                rates as directional signals rather than precise probabilities.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Sample Size Effects</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-3">
              <p>
                Low entry counts can create noisy win rates or conversion rates. Use matchup counts, total
                entries, and draw rates alongside win rate to assess stability.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
