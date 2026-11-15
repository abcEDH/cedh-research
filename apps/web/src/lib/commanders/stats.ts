import type { PodMetric, CommanderMetaEv } from "@/lib/schemas/api-contracts";
import type { PodMetricBadgeData } from "@/components/commanders/pod-metric-badges";

export function normalCdf(x: number): number {
  const sign = x >= 0 ? 1 : -1;
  const absX = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * absX);
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const erf =
    1 - (((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t) * Math.exp(-absX * absX);
  return 0.5 * (1 + sign * erf);
}

export function formatPValue(pValue: number): string {
  if (pValue < 0.001) return "<0.001";
  if (pValue < 0.01) return "<0.01";
  return pValue.toFixed(3);
}

export function computePValue(delta: number, stdDev: number, n: number): number {
  const zScore = delta / (stdDev / Math.sqrt(n));
  return 2 * (1 - normalCdf(Math.abs(zScore)));
}

const THREAT_TOOLTIP = "How often this deck wins the pod when it's at the table.";
const SURVIVABILITY_TOOLTIP = "How often this deck finishes 1st or 2nd.";
const META_EV_TOOLTIP = "Expected pod winrate weighted by realistic pod compositions.";

/**
 * Builds the three pod-metric badges (#151) from the raw get_pod_metrics (#148) and
 * get_commander_meta_ev (#149) rows. Pure/presentational-data-only: the page fetches the RPCs,
 * this shapes them, PodMetricBadges just renders. A commander outside the top-N metashare
 * window has no row in either RPC (podMetric/metaEv are null) and the badge is simply omitted
 * rather than rendered as a fake zero.
 *
 * get_commander_meta_ev has no significance flag of its own -- the EV badge reuses the pod
 * metrics row's is_statistically_significant (same underlying sample size, pods_present,
 * drives confidence in all three numbers for this commander) and its pods_present as the EV
 * badge's "N" (there is no literal per-triple sample size to show for a weighted-average
 * metric).
 */
export function buildPodMetricBadges(
  podMetric: PodMetric | null,
  metaEv: CommanderMetaEv | null
): {
  threat: PodMetricBadgeData | null;
  survivability: PodMetricBadgeData | null;
  metaEv: PodMetricBadgeData | null;
} {
  const threat: PodMetricBadgeData | null = podMetric
    ? {
        label: "Threat",
        value: podMetric.threat_score,
        ciLow: podMetric.threat_ci_low,
        ciHigh: podMetric.threat_ci_high,
        n: podMetric.pods_present,
        isStatisticallySignificant: podMetric.is_statistically_significant,
        tooltip: THREAT_TOOLTIP,
      }
    : null;

  const survivability: PodMetricBadgeData | null = podMetric
    ? {
        label: "Survivability",
        value: podMetric.survivability,
        ciLow: podMetric.survivability_ci_low,
        ciHigh: podMetric.survivability_ci_high,
        n: podMetric.pods_present,
        isStatisticallySignificant: podMetric.is_statistically_significant,
        tooltip: SURVIVABILITY_TOOLTIP,
      }
    : null;

  const metaEvBadge: PodMetricBadgeData | null = metaEv
    ? {
        label: "Meta EV",
        value: metaEv.meta_ev,
        ciLow: metaEv.meta_ev_ci_low,
        ciHigh: metaEv.meta_ev_ci_high,
        n: podMetric?.pods_present ?? 0,
        isStatisticallySignificant: podMetric?.is_statistically_significant ?? false,
        tooltip: META_EV_TOOLTIP,
      }
    : null;

  return { threat, survivability, metaEv: metaEvBadge };
}
