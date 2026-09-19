export type PlayerCommanderProfileRow = {
  active_commander: string | null;
  active_commander_prediction_score: number | null;
  latest_commander: string | null;
  latest_commander_date: string | null;
  commander_predictions:
    | Array<{
        commander: string;
        entries: number;
        prediction_share?: number | null;
        model_share?: number | null;
      }>
    | null;
};

/** Persisted prediction_share is normalized across all choices before top-three truncation.
 * Legacy model_share and active_commander_prediction_score may be raw weights.
 */
export function commanderPredictionRows(profile: PlayerCommanderProfileRow | null) {
  return (profile?.commander_predictions ?? [])
    .filter((row) => row.commander.trim() && row.commander.trim().toLowerCase() !== "unknown commander")
    .slice(0, 3)
    .map((row) => ({
      commander: row.commander,
      share: typeof row.prediction_share === "number" && Number.isFinite(row.prediction_share)
        && row.prediction_share >= 0 && row.prediction_share <= 1 ? row.prediction_share : null,
    }));
}
