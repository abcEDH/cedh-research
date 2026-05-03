import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function Loading() {
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8" aria-hidden>
          <div className="space-y-3">
            <div className="h-4 w-48 rounded bg-muted/40" />
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <div className="h-9 w-72 rounded bg-muted/40" />
              </div>
              <div className="h-4 w-36 rounded bg-muted/40" />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-9">
            {Array.from({ length: 9 }).map((_, i) => (
              <Card key={i} className="knd-panel">
                <CardHeader>
                  <div className="h-3 w-20 rounded bg-muted/40" />
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="h-7 w-16 rounded bg-muted/40" />
                  <div className="h-3 w-12 rounded bg-muted/40" />
                </CardContent>
              </Card>
            ))}
          </div>

          <SectionSkeleton label="Loading player profile…" />
          <SectionSkeleton label="Loading commander matchups…" />
          <SectionSkeleton label="Loading achievements…" />
        </div>
      </main>
    </div>
  );
}

function SectionSkeleton({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-border/40 bg-card/40 px-4 py-10 text-sm text-muted-foreground">
      {label}
    </div>
  );
}
