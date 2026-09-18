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
