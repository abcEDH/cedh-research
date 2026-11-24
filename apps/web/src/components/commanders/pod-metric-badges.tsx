import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export interface PodMetricBadgeData {
  label: string;
  /** 0-1 point estimate. */
  value: number;
  ciLow: number | null;
  ciHigh: number | null;
  /** Sample size shown alongside the CI (pods_present, "at the table" count). */
  n: number;
  isStatisticallySignificant: boolean;
  /** Plain-English definition shown in the tooltip, per #151. */
  tooltip: string;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function formatCi(ciLow: number | null, ciHigh: number | null): string {
  if (ciLow === null || ciHigh === null) return "insufficient data";
  return `${formatPercent(ciLow)}–${formatPercent(ciHigh)}`;
}

function Badge({ metric }: { metric: PodMetricBadgeData }) {
  const tooltipText = metric.isStatisticallySignificant
    ? metric.tooltip
    : `${metric.tooltip} Low confidence: based on a small sample size.`;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={`${metric.label}: ${formatPercent(metric.value)}. ${tooltipText}`}
          className={`min-h-11 flex-1 rounded-lg border border-border/60 bg-muted/30 px-4 py-3 text-center transition-opacity sm:min-h-0 ${
            metric.isStatisticallySignificant ? "" : "opacity-50"
          }`}
        >
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{metric.label}</p>
          <p className="mt-1 text-2xl font-semibold text-foreground">{formatPercent(metric.value)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatCi(metric.ciLow, metric.ciHigh)} {"·"} {metric.n.toLocaleString()} pods
          </p>
          {!metric.isStatisticallySignificant && (
            <p className="mt-0.5 text-[10px] uppercase tracking-[0.15em] text-[hsl(var(--knd-amber))]">
              Low confidence
            </p>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs leading-relaxed">{tooltipText}</TooltipContent>
    </Tooltip>
  );
}

/**
 * Header-strip badges for the commander detail page (#151): THREAT / SURVIVABILITY / META EV.
 * Purely presentational -- `page.tsx` fetches get_pod_metrics (#148) and get_commander_meta_ev
 * (#149) server-side and passes the parsed values in. Any metric the commander has no row for
 * (outside the top-N metashare window) is simply omitted, not rendered as a fake zero.
 */
export function PodMetricBadges({
  threat,
  survivability,
  metaEv,
}: {
  threat: PodMetricBadgeData | null;
  survivability: PodMetricBadgeData | null;
  metaEv: PodMetricBadgeData | null;
}) {
  const metrics = [threat, survivability, metaEv].filter((m): m is PodMetricBadgeData => m !== null);
  if (metrics.length === 0) return null;

  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row">
      {metrics.map((metric) => (
        <Badge key={metric.label} metric={metric} />
      ))}
    </div>
  );
}
