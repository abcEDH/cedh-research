import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata = {
  title: "Elo Methodology | cEDH Analytics",
  description: "How our 4-player cEDH Elo model is derived and implemented.",
};

export default function EloMethodologyPage() {
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
              cEDH Elo Methodology
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Derived from the TopDeck cEDH Skill Rating framework by Charles Lien and Alex Lien.
            </p>
          </div>
        </div>

        <Card className="mb-6 border-border/60 bg-card/60">
          <CardHeader>
            <CardTitle className="text-primary">Model Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              We model each game as a 4-player zero-sum event. Players have ratings and converted
              equity. Expected outcome is proportional to equity, and rating updates follow Elo
              style gradient steps.
            </p>
            <p>
              Player equity: <code>2^(R/200)</code>
            </p>
            <p>
              Expected share: <code>Eᵢ = equityᵢ / Σ equity</code>
            </p>
            <p>
              Result share: <code>Sᵢ = 1</code> (win), <code>0</code> (loss),{" "}
              <code>1/n</code> (draw with n players)
            </p>
            <p>
              Update rule: <code>R&#39; = R + K × (S - E)</code>, with <code>K = 30</code> in current
              implementation.
            </p>
          </CardContent>
        </Card>

        <Card className="mb-6 border-border/60 bg-card/60">
          <CardHeader>
            <CardTitle className="text-[hsl(var(--knd-amber))]">Implementation Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Initial rating is 1500 for unseen players.</p>
            <p>Games are processed chronologically.</p>
            <p>Draws are handled as fractional wins to preserve zero-sum accounting.</p>
            <p>Non-4-player games are included and draw value scales to player count.</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60">
          <CardHeader>
            <CardTitle className="text-muted-foreground">Reference</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              TopDeck document:{" "}
              <a
                href="https://topdeck.gg/elo/edh"
                target="_blank"
                rel="noreferrer"
                className="text-primary underline decoration-primary/40 underline-offset-4"
              >
                https://topdeck.gg/elo/edh
              </a>
            </p>
            <p>
              We also preserved a local methodology copy at{" "}
              <code>docs/methodology/cedh-skill-rating.md</code>.
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

