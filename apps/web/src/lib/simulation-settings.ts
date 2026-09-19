export type SimulationSettings = {
  swissRounds: number;
  topCut: number;
  runSeconds: number;
  dropAfterRound: number | null;
  dropMinPoints: number | null;
};

export function parseSimulationSettings(input: Record<keyof SimulationSettings, string>, defaults: SimulationSettings): SimulationSettings {
  function integer(key: keyof SimulationSettings, minimum: number, optional = false): number | null {
    const raw = input[key].trim();
    if (!raw && optional) return null;
    const value = raw ? Number(raw) : defaults[key];
    if (value === null || !Number.isSafeInteger(value) || value < minimum) {
      throw new Error(`${key} must be a whole number of at least ${minimum}.`);
    }
    return value;
  }
  const swissRounds = integer("swissRounds", 1)!;
  const topCut = integer("topCut", 0)!;
  const runSeconds = integer("runSeconds", 1)!;
  const dropAfterRound = integer("dropAfterRound", 1, true);
  const dropMinPoints = integer("dropMinPoints", 0, true);
  if (runSeconds > 600) throw new Error("Run duration must be at most 600 seconds.");
  if ((dropAfterRound === null) !== (dropMinPoints === null)) throw new Error("Provide both point-drop settings or leave both blank.");
  if (dropAfterRound !== null && dropAfterRound > swissRounds) throw new Error("The drop round must be within the Swiss rounds.");
  return { swissRounds, topCut, runSeconds, dropAfterRound, dropMinPoints };
}
