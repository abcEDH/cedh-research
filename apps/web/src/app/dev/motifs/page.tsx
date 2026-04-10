import Link from "next/link";
import Image from "next/image";
import { MotifLayer } from "@/components/motifs/MotifLayer";

export default function MotifPreviewPage() {
  return (
    <div className="min-h-screen knd-body p-12">
      <div className="grid gap-10">
        {(["A", "B", "C"] as const).map((v) => (
          <section key={v} className="relative knd-panel overflow-hidden p-12">
            <MotifLayer variant={v} intensity={0.95} className="absolute inset-0 z-0" />
            <div className="relative z-10 max-w-2xl">
              <div className="knd-chip mb-4">Motif variant {v}</div>
              <h1 className="text-4xl font-semibold tracking-tight">
                Kamigawa-flair overlays, but disciplined.
              </h1>
              <p className="mt-4 text-muted-foreground">
                This route is a visual QA harness: legibility, contrast, and “does it fight the UI?”
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link className="inline-flex items-center rounded-md bg-primary px-6 py-2 text-primary-foreground" href="/">
                  Back home
                </Link>
                <Link className="inline-flex items-center rounded-md border border-border/70 bg-muted/30 px-6 py-2" href="/commanders">
                  Open dashboard
                </Link>
              </div>
              <div className="mt-8 flex items-center gap-4">
                <div className="relative h-8 w-full">
                  <Image
                    src="/motifs/divider-sigil.svg"
                    alt=""
                    fill
                    sizes="100vw"
                    className="object-contain opacity-80"
                  />
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
