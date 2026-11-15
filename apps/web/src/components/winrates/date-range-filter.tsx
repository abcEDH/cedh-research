"use client";

import { useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DAYS_BACK_OPTIONS, parseDaysBack } from "@/lib/winrates/stats";

/**
 * Re-fetches server-side on change (navigates to a new `days` search param, which re-runs the
 * /winrates server component) -- unlike the row-sort controls in MatchupMatrixTable, which are
 * purely client-side and never touch the URL or the network.
 */
export default function DateRangeFilter() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const daysBack = parseDaysBack(searchParams.get("days") ?? undefined);

  function handleChange(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("days", value);
    startTransition(() => router.replace(`/winrates?${params.toString()}`, { scroll: false }));
  }

  return (
    <Select value={String(daysBack)} onValueChange={handleChange} disabled={isPending}>
      <SelectTrigger className="min-h-11 w-44 rounded-full bg-input/50 sm:min-h-9" aria-label="Date range">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {DAYS_BACK_OPTIONS.map((option) => (
          <SelectItem key={option.value} value={String(option.value)}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
