import { describe, it, expect } from "vitest";
import type { PodMetric, CommanderMetaEv } from "@/lib/schemas/api-contracts";
import { buildPodMetricBadges } from "@/lib/commanders/stats";

const COMMANDER_ID = "aaaaaaaa-0000-0000-0000-000000000001";

function podMetric(overrides: Partial<PodMetric> = {}): PodMetric {
  return {
    commander_id: COMMANDER_ID,
    pods_present: 1243,
    wins: 472,
    top_two: 870,
    threat_score: 0.38,
    threat_ci_low: 0.35,
    threat_ci_high: 0.41,
    survivability: 0.7,
    survivability_ci_low: 0.67,
    survivability_ci_high: 0.73,
    is_statistically_significant: true,
    ...overrides,
  };
}

function metaEv(overrides: Partial<CommanderMetaEv> = {}): CommanderMetaEv {
  return {
    commander_id: COMMANDER_ID,
    meta_ev: 0.3,
    meta_ev_ci_low: 0.26,
    meta_ev_ci_high: 0.34,
    composition_coverage: 0.82,
    pods_present: 1243,
    is_statistically_significant: true,
    ...overrides,
  };
}

describe("buildPodMetricBadges", () => {
  it("builds all three badges with the mocked RPC values (#151 badge contents example)", () => {
    const badges = buildPodMetricBadges(
      podMetric({ threat_score: 0.38, threat_ci_low: 0.35, threat_ci_high: 0.41, pods_present: 1243 }),
      metaEv({ pods_present: 1243 })
    );

    expect(badges.threat).toEqual({
      label: "Threat",
      value: 0.38,
      ciLow: 0.35,
      ciHigh: 0.41,
      n: 1243,
      isStatisticallySignificant: true,
      tooltip: "How often this deck wins the pod when it's at the table.",
    });
    expect(badges.survivability?.label).toBe("Survivability");
    expect(badges.survivability?.tooltip).toBe("How often this deck finishes 1st or 2nd.");
    expect(badges.metaEv).toEqual({
      label: "Meta EV",
      value: 0.3,
      ciLow: 0.26,
      ciHigh: 0.34,
      n: 1243,
      isStatisticallySignificant: true,
      tooltip: "Expected pod winrate weighted by realistic pod compositions.",
    });
  });

  it("propagates is_statistically_significant=false to reduce confidence on all three badges", () => {
    const badges = buildPodMetricBadges(
      podMetric({ is_statistically_significant: false }),
      metaEv({ is_statistically_significant: false })
    );

    expect(badges.threat?.isStatisticallySignificant).toBe(false);
    expect(badges.survivability?.isStatisticallySignificant).toBe(false);
    expect(badges.metaEv?.isStatisticallySignificant).toBe(false);
  });

  it("uses get_commander_meta_ev's own pods_present/significance, not get_pod_metrics', since the two can legitimately disagree (regression test, Codex review on PR #384)", () => {
    // get_pod_metrics counts every non-bye participation regardless of pod size (100 pods: 90
    // three-player + 10 four-player), while get_commander_meta_ev only ever aggregates over
    // exactly-4-player pods (10). Before this fix, the Meta EV badge borrowed podMetric's N and
    // would have claimed N=100 and significant=true for an estimate only 10 pods actually fed.
    const badges = buildPodMetricBadges(
      podMetric({ pods_present: 100, is_statistically_significant: true }),
      metaEv({ pods_present: 10, is_statistically_significant: false })
    );

    expect(badges.threat?.n).toBe(100);
    expect(badges.threat?.isStatisticallySignificant).toBe(true);
    expect(badges.metaEv?.n).toBe(10);
    expect(badges.metaEv?.isStatisticallySignificant).toBe(false);
  });

  it("omits threat/survivability when the commander has no pod_metrics row (outside top-N)", () => {
    const badges = buildPodMetricBadges(null, metaEv());

    expect(badges.threat).toBeNull();
    expect(badges.survivability).toBeNull();
  });

  it("omits the EV badge when the commander has no meta-EV row (outside top-N)", () => {
    const badges = buildPodMetricBadges(podMetric(), null);

    expect(badges.metaEv).toBeNull();
    expect(badges.threat).not.toBeNull();
  });

  it("omits every badge when the commander is outside the top-N window entirely", () => {
    const badges = buildPodMetricBadges(null, null);

    expect(badges.threat).toBeNull();
    expect(badges.survivability).toBeNull();
    expect(badges.metaEv).toBeNull();
  });
});
