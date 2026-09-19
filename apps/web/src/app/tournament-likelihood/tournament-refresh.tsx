"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";

export function TournamentRefresh({ updatedAt, failed }: { updatedAt: string | null; failed: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
      <button
        type="button"
        disabled={pending}
        onClick={() => startTransition(() => router.refresh())}
        className="min-h-11 rounded-md border border-border/70 px-4 py-2 text-foreground hover:border-primary/60 disabled:opacity-50"
      >
        {pending ? "Refreshing…" : "Refresh standings"}
      </button>
      <p role="status">
        {failed ? "Update failed. Try refreshing again." : updatedAt ? (
          <>Checked <time dateTime={updatedAt}>{new Date(updatedAt).toLocaleTimeString("en-GB", { timeZone: "UTC" })} UTC</time>. </>
        ) : null}
      </p>
    </div>
  );
}
